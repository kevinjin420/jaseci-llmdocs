"""Health route handlers"""
from flask import jsonify
from database import get_db
from database.models import BenchmarkResult, BenchmarkRun, Collection


def register_routes(app, socketio=None, running_benchmarks=None):

    @app.route('/api/running', methods=['GET'])
    def get_running():
        if running_benchmarks is None:
            return jsonify({'runs': {}})
        active = {k: v for k, v in running_benchmarks.items() if v.get('status') == 'running'}
        return jsonify({'runs': active})

    @app.route('/api/clear-db', methods=['POST'])
    def clear_database():
        with get_db() as session:
            deleted_results = session.query(BenchmarkResult).delete()
            deleted_runs = session.query(BenchmarkRun).delete()
            deleted_collections = session.query(Collection).delete()
        return jsonify({'status': 'success'})
