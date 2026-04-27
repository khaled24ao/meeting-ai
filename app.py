"""
Application entry point for MeetingAI.

Initializes environment variables and creates the Flask application instance.
Performs startup validation of required configuration.
"""
import os
import sys
from dotenv import load_dotenv
import logging

# Load environment variables from .env file before any other imports
load_dotenv()

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Startup validation: Check required environment variables ---
REQUIRED_ENV_VARS = {
    'GROQ_API_KEY': 'Groq API key (get from https://console.groq.com)',
    'SECRET_KEY': 'Secret key for sessions (generate a random 32+ character string)'
}

missing_vars = []
for var, description in REQUIRED_ENV_VARS.items():
    if not os.getenv(var):
        missing_vars.append(f"  - {var}: {description}")

if missing_vars:
    logger.error("=" * 60)
    logger.error("ERROR: Missing required environment variables:")
    for msg in missing_vars:
        logger.error(msg)
    logger.error("=" * 60)
    logger.error("Please create a .env file with the required variables.")
    logger.error("See .env.example for all available configuration options.")
    sys.exit(1)

logger.info("All required environment variables are present.")
logger.info("Configuration: PORT=%s, DEBUG=%s, LOG_LEVEL=%s",
            os.getenv('PORT', '7860'),
            os.getenv('DEBUG', 'false'),
            os.getenv('LOG_LEVEL', 'INFO'))

# Import and create Flask app (after env validation)
from backend.app import create_app
from flask import Flask

# Create Flask application instance
app: Flask = create_app()

if __name__ == "__main__":
    try:
        host: str = os.getenv('FLASK_HOST', '0.0.0.0')
        port_env: str = os.getenv('FLASK_PORT', os.getenv('PORT', '7860'))
        port: int = int(port_env)
        
        logger.info("Starting MeetingAI application on http://%s:%d", host, port)
        app.run(host=host, port=port, debug=app.config.get('DEBUG', False))
    except ValueError as e:
        logger.error("Invalid port configuration: %s", str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to start application: %s", str(e), exc_info=True)
        sys.exit(1)