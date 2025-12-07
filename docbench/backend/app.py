"""Flask application factory"""
import sys
import logging
import traceback
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

running_benchmarks = {}

__all__ = ['create_app', 'create_socketio', 'running_benchmarks']


def create_app(verbosity=1):
    """Create and configure Flask application

    Args:
        verbosity: Logging verbosity level (1-4)
            1 (-v): Basic - Frontend/backend + API communication (default)
            2 (-vv): Detailed - Add batch progress and evaluation
            3 (-vvv): Debug - Add detailed debugging info
            4 (-vvvv): Full Debug - All logging
    """
    app = Flask(__name__)

    log_level_map = {
        1: logging.INFO,
        2: logging.INFO,
        3: logging.DEBUG,
        4: logging.DEBUG
    }
    log_level = log_level_map.get(verbosity, logging.DEBUG)

    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    app.logger.setLevel(log_level)
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['VERBOSITY'] = verbosity

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error('=' * 80)
        app.logger.error('UNHANDLED EXCEPTION')
        app.logger.error('=' * 80)
        app.logger.error(f'Exception Type: {type(e).__name__}')
        app.logger.error(f'Exception Message: {str(e)}')
        app.logger.error('Traceback:')
        app.logger.error(traceback.format_exc())
        app.logger.error('=' * 80)
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }), 500

    CORS(app, origins='*', resources={r"/*": {"origins": "*"}})

    @app.before_request
    def log_request_info():
        verbosity = app.config.get('VERBOSITY', 1)

        if verbosity >= 4:
            app.logger.debug('=' * 60)
            app.logger.debug(f'REQUEST: {request.method} {request.path}')
            app.logger.debug(f'Remote Address: {request.remote_addr}')
            if request.args:
                app.logger.debug(f'Query Params: {dict(request.args)}')
            if request.is_json:
                app.logger.debug(f'JSON Body: {request.get_json()}')
            app.logger.debug('=' * 60)
        elif verbosity >= 1:
            app.logger.info(f'{request.method} {request.path}')

    @app.after_request
    def log_response_info(response):
        verbosity = app.config.get('VERBOSITY', 1)

        if verbosity >= 4:
            app.logger.debug(f'RESPONSE: {request.method} {request.path} - Status: {response.status_code}')
        elif verbosity >= 1:
            app.logger.info(f'{request.method} {request.path} - {response.status_code}')

        return response

    return app


def create_socketio(app, verbosity=1):
    """Create and configure SocketIO

    Args:
        app: Flask app instance
        verbosity: Logging verbosity level (1-4)
    """
    import logging

    socketio_logger = logging.getLogger('socketio')
    engineio_logger = logging.getLogger('engineio')

    if verbosity >= 4:
        socketio_logger.setLevel(logging.DEBUG)
        engineio_logger.setLevel(logging.DEBUG)
    elif verbosity >= 3:
        socketio_logger.setLevel(logging.INFO)
        engineio_logger.setLevel(logging.INFO)
    else:
        socketio_logger.setLevel(logging.WARNING)
        engineio_logger.setLevel(logging.WARNING)

    return SocketIO(
        app,
        cors_allowed_origins='*',
        async_mode='threading',
        logger=socketio_logger,
        engineio_logger=engineio_logger,
        ping_timeout=60,
        ping_interval=25
    )
