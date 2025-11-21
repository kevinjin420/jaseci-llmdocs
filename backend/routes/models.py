"""Model and variant route handlers"""
from flask import jsonify
from backend.services import LLMService
from database import DocumentationService


def register_routes(app, socketio=None, running_benchmarks=None):

    @app.route('/api/models', methods=['GET'])
    def get_models():
        llm_service = LLMService()
        models = llm_service.fetch_available_models()
        formatted = [
            {
                'id': m.get('id'),
                'name': m.get('name'),
                'context_length': m.get('context_length'),
                'pricing': m.get('pricing'),
                'architecture': m.get('architecture')
            }
            for m in models
        ]
        return jsonify({'models': formatted})

    @app.route('/api/variants', methods=['GET'])
    def get_variants():
        variants = DocumentationService.get_all_variants()
        return jsonify({'variants': variants})
