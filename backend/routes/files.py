"""File route handlers"""
from flask import jsonify, request, Response
import csv
import io
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
            'total_tests': str(result.get('total_tests', 0)),
            'batch_size': result.get('batch_size'),
            'num_batches': result.get('num_batches')
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
        with get_db() as session:
            query = session.query(BenchmarkResult).filter(
                BenchmarkResult.collection_id.is_(None)
            ).order_by(BenchmarkResult.created_at.desc()).limit(limit)
            results = [
                {
                    'id': r.id,
                    'run_id': r.run_id,
                    'model': r.model,
                    'variant': r.variant,
                    'test_suite': r.test_suite,
                    'total_tests': r.total_tests,
                    'batch_size': r.batch_size,
                    'num_batches': r.num_batches,
                    'total_score': r.total_score,
                    'max_score': r.max_score,
                    'percentage': r.percentage,
                    'created_at': r.created_at,
                    'responses': r.responses,
                }
                for r in query.all()
            ]
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

    @app.route('/api/stash-selected', methods=['POST'])
    def stash_selected():
        data = request.json
        run_ids = data.get('run_ids', [])
        if not run_ids:
            return jsonify({'error': 'run_ids is required'}), 400

        collection_name = f"collection-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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

    @app.route('/api/clean', methods=['POST'])
    def clean():
        with get_db() as session:
            deleted = session.query(BenchmarkResult).filter(
                BenchmarkResult.collection_id.is_(None)
            ).delete()
        return jsonify({'status': 'success', 'deleted': deleted})

    @app.route('/api/export-collections-csv', methods=['POST'])
    def export_collections_csv():
        data = request.json
        collection_names = data.get('collections', [])
        if not collection_names:
            return jsonify({'error': 'collections is required'}), 400

        rows = []
        for collection_name in collection_names:
            results = BenchmarkResultService.get_collection_results(collection_name)
            for result in results:
                rows.append({
                    'collection': collection_name,
                    'run_id': result.get('run_id'),
                    'model': result.get('model'),
                    'variant': result.get('variant'),
                    'test_suite': result.get('test_suite'),
                    'batch_size': result.get('batch_size'),
                    'num_batches': result.get('num_batches'),
                    'total_tests': result.get('total_tests'),
                    'total_score': result.get('total_score'),
                    'max_score': result.get('max_score'),
                    'percentage': result.get('percentage'),
                    'temperature': result.get('temperature'),
                    'max_tokens': result.get('max_tokens'),
                    'created_at': result.get('created_at'),
                })

        if not rows:
            return jsonify({'error': 'No results found'}), 404

        output = io.StringIO()
        fieldnames = [
            'collection', 'run_id', 'model', 'variant', 'test_suite',
            'batch_size', 'num_batches', 'total_tests',
            'total_score', 'max_score', 'percentage',
            'temperature', 'max_tokens', 'created_at'
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=collections-export.csv'}
        )
