"""File route handlers"""
from flask import jsonify, request
import json
from datetime import datetime
from pathlib import Path
from database import BenchmarkResultService, get_db
from database.models import BenchmarkResult


def _format_result(result, collection=None):
    responses_json = json.dumps(result.get('responses', {}))
    return {
        'name': result['run_id'],
        'path': f"db/{result['run_id']}",
        'size': len(responses_json.encode('utf-8')),
        'modified': result['created_at'],
        'metadata': {
            'model': result['model'],
            'model_full': result['model'],
            'variant': result['variant'],
            'test_suite': result['test_suite'],
            'total_tests': str(result.get('total_tests', 0))
        },
        'db_id': result['id'],
        'run_id': result['run_id'],
        'score': result.get('total_score'),
        'max_score': result.get('max_score'),
        'percentage': result.get('percentage'),
        'collection': collection or result.get('collection')
    }


def register_routes(app, socketio=None, running_benchmarks=None):

    @app.route('/api/test-files', methods=['GET'])
    def get_test_files():
        limit = request.args.get('limit', 50, type=int)
        results = BenchmarkResultService.get_recent(limit=limit)
        return jsonify({'files': [_format_result(r) for r in results]})

    @app.route('/api/stashes', methods=['GET'])
    def get_stashes():
        return jsonify({'stashes': BenchmarkResultService.get_collections()})

    @app.route('/api/stash/<stash_name>/files', methods=['GET'])
    def get_stash_files(stash_name):
        results = BenchmarkResultService.get_collection_results(stash_name)
        return jsonify({'files': [_format_result(r, stash_name) for r in results]})

    @app.route('/api/stash/<stash_name>', methods=['DELETE'])
    def delete_stash(stash_name):
        BenchmarkResultService.delete_collection(stash_name)
        return jsonify({'status': 'success'})

    @app.route('/api/stash', methods=['POST'])
    def stash():
        with get_db() as session:
            uncollected = session.query(BenchmarkResult).filter(
                BenchmarkResult.collection_id.is_(None)
            ).all()
            if not uncollected:
                return jsonify({'status': 'info', 'message': 'No uncollected results'})

            collection_name = f"collection-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_ids = [r.run_id for r in uncollected]
            BenchmarkResultService.add_to_collection(run_ids, collection_name)

            return jsonify({
                'status': 'success',
                'collection_name': collection_name,
                'count': len(run_ids)
            })

    @app.route('/api/delete-file', methods=['POST'])
    def delete_file():
        data = request.json
        file_path = data.get('file_path')
        if not file_path:
            return jsonify({'error': 'file_path is required'}), 400

        run_id = file_path.replace('db/', '') if file_path.startswith('db/') else Path(file_path).stem
        deleted = BenchmarkResultService.delete_by_run_id(run_id)
        if deleted:
            return jsonify({'status': 'success'})
        return jsonify({'error': 'Result not found'}), 404
