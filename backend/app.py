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


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    app.logger.setLevel(logging.DEBUG)
    app.config['PROPAGATE_EXCEPTIONS'] = True

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
        app.logger.debug('=' * 60)
        app.logger.debug(f'REQUEST: {request.method} {request.path}')
        app.logger.debug(f'Remote Address: {request.remote_addr}')
        if request.args:
            app.logger.debug(f'Query Params: {dict(request.args)}')
        if request.is_json:
            app.logger.debug(f'JSON Body: {request.get_json()}')
        app.logger.debug('=' * 60)

    @app.after_request
    def log_response_info(response):
        app.logger.debug(f'RESPONSE: {request.method} {request.path} - Status: {response.status_code}')
        return response

    return app


def create_socketio(app):
    """Create and configure SocketIO"""
    import logging

    # Create custom logger for SocketIO that filters PING/PONG
    socketio_logger = logging.getLogger('socketio')
    engineio_logger = logging.getLogger('engineio')

    # Set to WARNING to suppress PING/PONG info messages
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
