"""
Flask application factory for MeetingAI.

Creates and configures the Flask application with blueprints,
CORS, logging, security headers, authentication, rate limiting, and error handlers.
"""
import os
import logging
from pathlib import Path
from typing import Any, Tuple, Union, Optional
from flask import Flask, render_template, jsonify, g, request, Response
from flask_cors import CORS

from backend.config import config
from backend.exceptions import MeetingAIError, ValidationError, TranscriptionError, AIServiceError, FileProcessingError
from backend.utils.auth import authenticate_api_key, rate_limit, get_rate_limit_stats


def create_app() -> Flask:
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application instance.
    """
    # Determine template directory path
    template_dir: Path = Path(__file__).parent.parent / 'templates'
    app: Flask = Flask(__name__, template_folder=str(template_dir))
    
    # Configure CORS - restrict to known origins in production
    if config.debug:
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:
        # In production, origins should be configured via environment variable
        allowed_origins: list[str] = os.getenv('ALLOWED_ORIGINS', 'https://yourdomain.com').split(',')
        CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
    
    # Configure Flask application settings
    app.config['UPLOAD_FOLDER'] = config.upload_folder
    app.config['MAX_CONTENT_LENGTH'] = config.max_upload_size
    app.config['DEBUG'] = config.debug
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.get('logging.level', 'INFO')),
        format=config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    
    logger: logging.Logger = logging.getLogger(__name__)
    logger.info("Initializing MeetingAI application")
    
    # Register blueprints
    from backend.routes.summarize import summarize_bp
    app.register_blueprint(summarize_bp, url_prefix='/api/v1')
    logger.info("Registered summarize blueprint at /api/v1")
    
    # Register before request hook for rate limiting
    @app.before_request
    def check_rate_limit() -> Optional[Response]:
        """Check rate limit before processing request (skip for health endpoint)."""
        try:
            # Skip rate limiting for health check (public)
            if request.path == '/api/v1/health' or request.path == '/':
                return None
            
            allowed, limit_info = rate_limit()
            if not allowed:
                return jsonify({
                    'success': False,
                    'error': 'RATE_LIMIT_EXCEEDED',
                    'message': 'Rate limit exceeded. Please try again later.',
                    'limit': limit_info
                }), 429
            
            # Store rate limit info for response headers
            g.rate_limit_info = limit_info
            return None
        except Exception as e:
            logger.error("Error in before_request rate limit check: %s", str(e), exc_info=True)
            return None # Fail open
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register after request hooks for security headers and rate limit headers
    @app.after_request
    def add_security_headers(response: Response) -> Response:
        """Add security headers to all responses."""
        try:
            # Content Security Policy
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            # HTTP Strict Transport Security (only send over HTTPS in production)
            if not config.debug:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            # Prevent MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            # XSS protection
            response.headers['X-XSS-Protection'] = '1; mode=block'
            # Referrer policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        except Exception as e:
            logger.error("Error adding security headers: %s", str(e))
        return response
    
    @app.after_request
    def add_rate_limit_headers(response: Response) -> Response:
        """Add rate limit headers to response."""
        try:
            if hasattr(g, 'rate_limit_info') and g.rate_limit_info is not None:
                info: dict[str, Any] = g.rate_limit_info
                response.headers['X-RateLimit-Limit'] = str(info.get('limit', 0))
                response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', 0))
                response.headers['X-RateLimit-Window'] = str(info.get('window_seconds', 0))
        except Exception as e:
            logger.error("Error adding rate limit headers: %s", str(e))
        return response
    
    @app.route('/')
    def index() -> str:
        """Render the main index page."""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error("Error rendering index template: %s", str(e), exc_info=True)
            return "MeetingAI is running. (Error loading UI)"
    
    logger.info("Application startup complete")
    return app


def register_error_handlers(app: Flask) -> None:
    """
    Register global error handlers for standardized error responses.
    
    Args:
        app: Flask application instance.
    """
    logger: logging.Logger = logging.getLogger(__name__)
    
    @app.errorhandler(401)
    def handle_unauthorized(error: Any) -> Tuple[Response, int]:
        """Handle 401 Unauthorized."""
        return jsonify({
            'success': False,
            'error': 'UNAUTHORIZED',
            'message': 'Authentication required. Provide valid X-API-Key header.'
        }), 401
    
    @app.errorhandler(429)
    def handle_rate_limit(error: Any) -> Tuple[Response, int]:
        """Handle 429 Too Many Requests."""
        return jsonify({
            'success': False,
            'error': 'RATE_LIMIT_EXCEEDED',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> Tuple[Response, int]:
        """Handle 400 Bad Request errors."""
        logger.warning("Validation error: %s", error)
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(error)
        }), 400
    
    @app.errorhandler(TranscriptionError)
    def handle_transcription_error(error: TranscriptionError) -> Tuple[Response, int]:
        """Handle 500 Internal Server Error for transcription failures."""
        logger.error("Transcription error: %s", error, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'TRANSCRIPTION_ERROR',
            'message': str(error) if config.debug else 'Transcription service encountered an error'
        }), 500
    
    @app.errorhandler(AIServiceError)
    def handle_ai_service_error(error: AIServiceError) -> Tuple[Response, int]:
        """Handle 503 Service Unavailable for AI service failures."""
        logger.error("AI service error: %s", error, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'AI_SERVICE_UNAVAILABLE',
            'message': str(error) if config.debug else 'AI analysis service is currently unavailable'
        }), 503
    
    @app.errorhandler(FileProcessingError)
    def handle_file_processing_error(error: FileProcessingError) -> Tuple[Response, int]:
        """Handle 400 Bad Request for file processing errors."""
        logger.warning("File processing error: %s", error)
        return jsonify({
            'success': False,
            'error': 'FILE_PROCESSING_ERROR',
            'message': str(error)
        }), 400
    
    @app.errorhandler(404)
    def handle_not_found(error: Any) -> Tuple[Response, int]:
        """Handle 404 Not Found."""
        return jsonify({
            'success': False,
            'error': 'NOT_FOUND',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error: Any) -> Tuple[Response, int]:
        """Handle 405 Method Not Allowed."""
        return jsonify({
            'success': False,
            'error': 'METHOD_NOT_ALLOWED',
            'message': 'The requested method is not allowed for this endpoint'
        }), 405
    
    @app.errorhandler(413)
    def handle_request_entity_too_large(error: Any) -> Tuple[Response, int]:
        """Handle 413 Request Entity Too Large."""
        return jsonify({
            'success': False,
            'error': 'REQUEST_TOO_LARGE',
            'message': 'Request exceeds maximum allowed size'
        }), 413
    
    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception) -> Tuple[Response, int]:
        """
        Handle all unhandled exceptions.
        
        Logs the full error but returns a generic message to avoid
        exposing internal details.
        """
        logger.error("Unhandled exception: %s", error, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'INTERNAL_SERVER_ERROR',
            'message': str(error) if config.debug else 'An unexpected error occurred'
        }), 500



if __name__ == '__main__':
    flask_app = create_app()
    logger = logging.getLogger(__name__)
    logger.info("Starting development server on %s:%s", config.host, config.port)
    flask_app.run(host=config.host, port=config.port, debug=config.debug)