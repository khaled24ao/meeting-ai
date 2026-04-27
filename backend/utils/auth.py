"""
Authentication and rate limiting utilities for MeetingAI.

Provides API key authentication and request rate limiting.
"""
import time
from functools import wraps
from typing import Dict, Tuple, Optional, Any, Callable
from flask import request, jsonify, g, Response
import logging

from backend.config import config

logger = logging.getLogger(__name__)

# In-memory rate limit store (use Redis in production)
_rate_limit_store: Dict[str, list] = {}


def authenticate_api_key(f: Callable) -> Callable:
    """
    Decorator to require valid API key for endpoint access.
    
    Checks X-API-Key header against ALLOWED_API_KEYS from config.
    Uses constant-time comparison to prevent timing attacks.
    
    Example:
        @app.route('/protected')
        @authenticate_api_key
        def protected():
            return jsonify({'status': 'ok'})
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        try:
            # Extract API key from header
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                logger.warning("Request missing X-API-Key header from %s", request.remote_addr)
                return jsonify({
                    'success': False,
                    'error': 'UNAUTHORIZED',
                    'message': 'API key required. Provide X-API-Key header.'
                }), 401
            
            # Validate API key
            if not config.is_valid_api_key(api_key):
                logger.warning("Invalid API key used from %s", request.remote_addr)
                return jsonify({
                    'success': False,
                    'error': 'UNAUTHORIZED',
                    'message': 'Invalid API key'
                }), 401
            
            # Store authenticated user info in Flask g object
            g.api_key = api_key[:8] + '...'  # Store partial for logging
            logger.debug("Authenticated request with API key %s from %s", g.api_key, request.remote_addr)
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error("Authentication error: %s", str(e), exc_info=True)
            return jsonify({
                'success': False,
                'error': 'INTERNAL_SERVER_ERROR',
                'message': 'An error occurred during authentication'
            }), 500
    
    return decorated_function


def rate_limit() -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if current client is within rate limits.
    
    Uses in-memory store with sliding window. For production,
    should use Redis for distributed rate limiting.
    
    Returns:
        Tuple of (is_allowed, limit_info_dict)
        
    Example:
        allowed, info = rate_limit()
        if not allowed:
            return jsonify({
                'success': False,
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': 'Rate limit exceeded',
                'limit': info
            }), 429
    """
    try:
        if not config.rate_limit_enabled:
            return True, None
        
        # Get client identifier (API key or IP address)
        client_id = g.get('api_key') or request.remote_addr or 'unknown'
        
        now = time.time()
        window_start = now - config.rate_limit_window
        
        # Initialize store for this client
        if client_id not in _rate_limit_store:
            _rate_limit_store[client_id] = []
        
        # Remove requests outside current window
        _rate_limit_store[client_id] = [
            timestamp for timestamp in _rate_limit_store[client_id]
            if timestamp > window_start
        ]
        
        # Check current count
        request_count = len(_rate_limit_store[client_id])
        
        if request_count >= config.rate_limit_requests:
            logger.warning("Rate limit exceeded for client %s: %d/%d requests",
                          client_id, request_count, config.rate_limit_requests)
            return False, {
                'client_id': client_id,
                'requests': request_count,
                'limit': config.rate_limit_requests,
                'window_seconds': config.rate_limit_window,
                'reset_at': min(_rate_limit_store[client_id]) + config.rate_limit_window if _rate_limit_store[client_id] else now
            }
        
        # Record this request
        _rate_limit_store[client_id].append(now)
        
        return True, {
            'client_id': client_id,
            'requests': request_count + 1,
            'limit': config.rate_limit_requests,
            'remaining': config.rate_limit_requests - (request_count + 1),
            'window_seconds': config.rate_limit_window
        }
    except Exception as e:
        logger.error("Rate limit check error: %s", str(e), exc_info=True)
        # Fail open or closed? Usually fail open for rate limiting to avoid blocking users on internal errors
        return True, None


def clear_rate_limit_store() -> None:
    """Clear in-memory rate limit store (useful for testing)."""
    _rate_limit_store.clear()


def get_rate_limit_stats() -> Dict[str, Any]:
    """Get current rate limit statistics (admin/debug endpoint)."""
    return {
        'active_clients': len(_rate_limit_store),
        'clients': {
            client_id: len(timestamps)
            for client_id, timestamps in _rate_limit_store.items()
        }
    }