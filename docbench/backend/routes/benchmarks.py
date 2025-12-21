"""Benchmark route handlers"""
from flask import jsonify, request
import threading
import traceback
import uuid
from pathlib import Path
from backend.services import LLMService, EvaluatorService
from backend.utils.logger import log_info, log_debug, log_error
from database import BenchmarkRunService, BenchmarkResultService


def register_routes(app, socketio, running_benchmarks):

    TESTS_DIR = Path('tests')

    @app.route('/api/benchmark/run', methods=['POST'])
    def run_benchmark():
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        data = request.json
        model = data.get('model')
        variant = data.get('variant')
        temperature = data.get('temperature', 0.1)
        max_tokens = data.get('max_tokens', 16000)
        batch_size = data.get('batch_size', 45)
        custom_batch_sizes = data.get('custom_batch_sizes')

        if not model or not variant:
            return jsonify({'error': 'model and variant are required'}), 400

        run_id = f"{model}_{variant}_{uuid.uuid4().hex[:8]}"

        def run_in_background():
            try:
                running_benchmarks[run_id] = {'status': 'running', 'progress': 'Initializing...'}
                socketio.emit('benchmark_update', {'run_id': run_id, 'status': 'running', 'progress': 'Initializing...'})

                llm_service = LLMService(api_key=api_key)
                BenchmarkRunService.create(
                    run_id=run_id, model=model, model_id=model, variant=variant,
                    temperature=temperature, max_tokens=max_tokens
                )

                def progress_callback(completed, total, message, batch_num=None, num_batches=None, failed=0, batch_statuses=None):
                    progress_text = f'{message} ({completed}/{total} tests)'
                    running_benchmarks[run_id].update({
                        'progress': progress_text,
                        'completed': completed,
                        'total': total,
                        'failed': failed,
                        'batch_num': batch_num,
                        'num_batches': num_batches,
                        'batch_statuses': batch_statuses,
                    })
                    update_data = {
                        'run_id': run_id, 'status': 'running', 'progress': progress_text,
                        'completed': completed, 'total': total, 'failed': failed
                    }
                    if batch_num is not None:
                        update_data['batch_num'] = batch_num
                        update_data['num_batches'] = num_batches
                    if batch_statuses is not None:
                        update_data['batch_statuses'] = batch_statuses
                    socketio.emit('benchmark_update', update_data)

                result = llm_service.run_benchmark_concurrent(
                    model, variant, temperature, max_tokens,
                    batch_size=batch_size, custom_batch_sizes=custom_batch_sizes, progress_callback=progress_callback
                )

                # Trigger evaluation immediately
                actual_run_id = result.get('run_id', run_id)
                log_info(f"[EVAL] Starting evaluation for {actual_run_id}", min_verbosity=2)
                socketio.emit('benchmark_update', {'run_id': run_id, 'status': 'evaluating', 'progress': 'Evaluating responses...'})

                from database import BenchmarkResultService
                result_data = BenchmarkResultService.get_by_run_id(actual_run_id)

                if result_data:
                    try:
                        log_debug(f"[EVAL] Setting evaluation status to 'evaluating' for {actual_run_id}", min_verbosity=3)
                        BenchmarkResultService.set_evaluation_status(actual_run_id, 'evaluating')

                        log_debug(f"[EVAL] Creating evaluator and evaluating responses...", min_verbosity=3)
                        evaluator = EvaluatorService()
                        eval_result = evaluator.evaluate_responses(result_data['responses'])

                        log_info(f"[EVAL] Updating evaluation results: {eval_result['percentage']:.2f}%", min_verbosity=2)
                        # Update evaluation
                        BenchmarkResultService.update_evaluation(
                            run_id=actual_run_id,
                            evaluation_results={
                                'category_breakdown': eval_result['evaluation_results'],
                                'level_breakdown': eval_result.get('level_breakdown', {})
                            },
                            total_score=eval_result['total_score'],
                            max_score=eval_result['max_score'],
                            percentage=eval_result['percentage']
                        )

                        log_info(f"[EVAL] Evaluation completed successfully for {actual_run_id}", min_verbosity=2)
                    except Exception as e:
                        log_error(f"[EVAL] Evaluation failed for {actual_run_id}: {e}")
                        traceback.print_exc()
                        BenchmarkResultService.set_evaluation_status(actual_run_id, 'failed')
                else:
                    log_error(f"[EVAL] Could not find result data for {actual_run_id}")

                running_benchmarks[run_id] = {'status': 'completed', 'result': result, 'progress': 'Done'}
                BenchmarkRunService.complete(run_id=actual_run_id, result_id=None)
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

        # Check evaluation status
        eval_status = result.get('evaluation_status')
        if eval_status == 'evaluating':
            return jsonify({
                'status': 'evaluating',
                'message': 'Evaluation in progress. Please wait...',
                'run_id': run_id
            }), 202  # 202 Accepted

        if eval_status == 'failed':
            return jsonify({
                'status': 'failed',
                'message': 'Evaluation failed',
                'run_id': run_id
            }), 500

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
                    'tests_completed': eval_result.get('tests_completed', 0)
                },
                'run_id': result.get('run_id'),
                'model': result.get('model'),
                'model_id': result.get('model_id'),
                'variant': result.get('variant'),
                'temperature': result.get('temperature'),
                'max_tokens': result.get('max_tokens'),
                'total_tests': result.get('total_tests', 0),
                'batch_size': result.get('batch_size'),
                'num_batches': result.get('num_batches'),
                'created_at': result.get('created_at'),
                'evaluated_at': result.get('evaluated_at'),
                'status': result.get('status')
            })

        category_breakdown = eval_results.get('category_breakdown', {})
        tests_completed = sum(len(c.get('tests', [])) for c in category_breakdown.values())

        return jsonify({
            'summary': {
                'total_score': result['total_score'],
                'total_max': result['max_score'],
                'overall_percentage': result['percentage'],
                'category_breakdown': category_breakdown,
                'level_breakdown': eval_results.get('level_breakdown', {}),
                'tests_completed': tests_completed
            },
            'run_id': result.get('run_id'),
            'model': result.get('model'),
            'model_id': result.get('model_id'),
            'variant': result.get('variant'),
            'temperature': result.get('temperature'),
            'max_tokens': result.get('max_tokens'),
            'total_tests': result.get('total_tests', 0),
            'batch_size': result.get('batch_size'),
            'num_batches': result.get('num_batches'),
            'created_at': result.get('created_at'),
            'evaluated_at': result.get('evaluated_at'),
            'status': result.get('status')
        })

    @app.route('/api/benchmark/rerun-batch', methods=['POST'])
    def rerun_batch():
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401

        data = request.json
        run_id = data.get('run_id')
        batch_num = data.get('batch_num')

        if not run_id or batch_num is None:
            return jsonify({'error': 'run_id and batch_num are required'}), 400

        result = BenchmarkResultService.get_by_run_id(run_id)
        if not result:
            return jsonify({'error': 'Result not found'}), 404

        model = result.get('model')
        variant = result.get('variant')
        temperature = result.get('temperature', 0.1)
        max_tokens = result.get('max_tokens', 16000)
        batch_size = result.get('batch_size', 45)

        rerun_id = f"rerun_{run_id}_{batch_num}"

        def run_in_background():
            try:
                running_benchmarks[rerun_id] = {
                    'status': 'running',
                    'progress': f'Rerunning batch {batch_num}...',
                    'original_run_id': run_id,
                    'batch_num': batch_num
                }
                socketio.emit('batch_rerun_update', {
                    'rerun_id': rerun_id,
                    'run_id': run_id,
                    'batch_num': batch_num,
                    'status': 'running'
                })

                llm_service = LLMService(api_key=api_key)
                batch_responses = llm_service.rerun_single_batch(
                    model, variant, temperature, max_tokens,
                    batch_num=batch_num, batch_size=batch_size
                )

                current_responses = result.get('responses', {})
                current_responses.update(batch_responses)
                BenchmarkResultService.update_responses(run_id, current_responses)

                running_benchmarks[rerun_id] = {
                    'status': 'completed',
                    'progress': f'Batch {batch_num} completed',
                    'responses': batch_responses
                }
                socketio.emit('batch_rerun_update', {
                    'rerun_id': rerun_id,
                    'run_id': run_id,
                    'batch_num': batch_num,
                    'status': 'completed',
                    'num_responses': len(batch_responses)
                })

            except Exception as e:
                app.logger.error(f'Batch rerun failed: {rerun_id} - {e}')
                app.logger.error(traceback.format_exc())
                running_benchmarks[rerun_id] = {'status': 'failed', 'error': str(e)}
                socketio.emit('batch_rerun_update', {
                    'rerun_id': rerun_id,
                    'run_id': run_id,
                    'batch_num': batch_num,
                    'status': 'failed',
                    'error': str(e)
                })

        threading.Thread(target=run_in_background).start()
        return jsonify({'rerun_id': rerun_id, 'status': 'started', 'batch_num': batch_num})

    @app.route('/api/evaluate-collection', methods=['POST'])
    def evaluate_collection():
        data = request.json
        collection_name = data.get('collection')
        if not collection_name:
            return jsonify({'error': 'collection is required'}), 400

        results = BenchmarkResultService.get_collection_results(collection_name)
        if not results:
            return jsonify({'error': 'Collection not found or empty'}), 404

        evaluated = {}
        for result in results:
            run_id = result['run_id']
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
                evaluated[run_id] = {
                    'summary': {
                        'overall_percentage': eval_result['percentage'],
                        'total_score': eval_result['total_score'],
                        'total_max': eval_result['max_score'],
                        'tests_completed': eval_result.get('tests_completed', 0),
                        'category_breakdown': eval_result['evaluation_results']
                    }
                }
            else:
                category_breakdown = eval_results.get('category_breakdown', {})
                tests_completed = sum(len(c.get('tests', [])) for c in category_breakdown.values())
                evaluated[run_id] = {
                    'summary': {
                        'overall_percentage': result.get('percentage', 0),
                        'total_score': result.get('total_score', 0),
                        'total_max': result.get('max_score', 0),
                        'tests_completed': tests_completed,
                        'category_breakdown': category_breakdown
                    }
                }

        return jsonify({
            'status': 'success',
            'collection': collection_name,
            'files_evaluated': len(evaluated),
            'results': evaluated
        })
