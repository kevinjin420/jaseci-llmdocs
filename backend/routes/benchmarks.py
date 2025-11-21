"""Benchmark route handlers"""
from flask import jsonify, request
import threading
import traceback
import os
from pathlib import Path
from backend.services import LLMService, EvaluatorService
from database import BenchmarkRunService, BenchmarkResultService


def register_routes(app, socketio, running_benchmarks):

    TESTS_DIR = Path('tests')

    @app.route('/api/benchmark/run', methods=['POST'])
    def run_benchmark():
        data = request.json
        model = data.get('model')
        variant = data.get('variant')
        temperature = data.get('temperature', 0.1)
        max_tokens = data.get('max_tokens', 16000)
        test_limit = data.get('test_limit')

        if not model or not variant:
            return jsonify({'error': 'model and variant are required'}), 400

        run_id = f"{model}_{variant}_{int(os.times().elapsed * 1000)}"

        def run_in_background():
            try:
                running_benchmarks[run_id] = {'status': 'running', 'progress': 'Initializing...'}
                socketio.emit('benchmark_update', {'run_id': run_id, 'status': 'running', 'progress': 'Initializing...'})

                llm_service = LLMService()
                BenchmarkRunService.create(
                    run_id=run_id, model=model, model_id=model, variant=variant,
                    temperature=temperature, max_tokens=max_tokens, test_limit=test_limit, concurrency=1
                )

                def progress_callback(completed, total, message, batch_num=None, num_batches=None):
                    progress_text = f'{message} ({completed}/{total} tests)'
                    running_benchmarks[run_id]['progress'] = progress_text
                    update_data = {
                        'run_id': run_id, 'status': 'running', 'progress': progress_text,
                        'completed': completed, 'total': total
                    }
                    if batch_num is not None:
                        update_data['batch_num'] = batch_num
                        update_data['num_batches'] = num_batches
                    socketio.emit('benchmark_update', update_data)

                result = llm_service.run_benchmark_concurrent(
                    model, variant, temperature, max_tokens,
                    test_limit=test_limit, progress_callback=progress_callback
                )

                running_benchmarks[run_id] = {'status': 'completed', 'result': result, 'progress': 'Done'}
                BenchmarkRunService.complete(run_id=result.get('run_id', run_id), result_id=None)
                socketio.emit('benchmark_update', {'run_id': run_id, 'status': 'completed', 'result': result})

            except Exception as e:
                app.logger.error(f'Benchmark failed: {run_id} - {e}')
                app.logger.error(traceback.format_exc())
                running_benchmarks[run_id] = {'status': 'failed', 'error': str(e), 'progress': 'Failed'}
                BenchmarkRunService.fail(run_id=run_id, error_message=str(e))
                socketio.emit('benchmark_update', {'run_id': run_id, 'status': 'failed', 'error': str(e)})

        threading.Thread(target=run_in_background).start()
        return jsonify({'run_id': run_id, 'status': 'started'})

    @app.route('/api/evaluate', methods=['POST'])
    def evaluate():
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        file_path = data.get('file')
        run_id = data.get('run_id')

        if not file_path and not run_id:
            return jsonify({'error': 'file or run_id is required'}), 400

        if file_path and not run_id:
            run_id = file_path.split('/')[-1].replace('.txt', '')

        result = BenchmarkResultService.get_by_run_id(run_id)
        if not result:
            return jsonify({'error': 'Result not found'}), 404

        eval_results = result.get('evaluation_results')
        needs_eval = not eval_results or 'category_breakdown' not in eval_results

        if needs_eval:
            evaluator = EvaluatorService()
            eval_result = evaluator.evaluate_responses(result['responses'])

            BenchmarkResultService.update_evaluation(
                run_id=run_id,
                evaluation_results={
                    'category_breakdown': eval_result['evaluation_results'],
                    'level_breakdown': eval_result.get('level_breakdown', {})
                },
                total_score=eval_result['total_score'],
                max_score=eval_result['max_score'],
                percentage=eval_result['percentage']
            )

            return jsonify({
                'summary': {
                    'total_score': eval_result['total_score'],
                    'total_max': eval_result['max_score'],
                    'overall_percentage': eval_result['percentage'],
                    'category_breakdown': eval_result['evaluation_results'],
                    'level_breakdown': eval_result.get('level_breakdown', {}),
                    'tests_completed': eval_result.get('tests_completed', 0),
                    'patched_count': eval_result.get('patched_count', 0)
                },
                'total_tests': result.get('total_tests', 0)
            })

        category_breakdown = eval_results.get('category_breakdown', {})
        tests_completed = sum(len(c.get('tests', [])) for c in category_breakdown.values())
        patched_count = sum(
            1 for c in category_breakdown.values()
            for t in c.get('tests', []) if t.get('was_patched')
        )

        return jsonify({
            'summary': {
                'total_score': result['total_score'],
                'total_max': result['max_score'],
                'overall_percentage': result['percentage'],
                'category_breakdown': category_breakdown,
                'level_breakdown': eval_results.get('level_breakdown', {}),
                'tests_completed': tests_completed,
                'patched_count': patched_count
            },
            'total_tests': result.get('total_tests', 0)
        })
