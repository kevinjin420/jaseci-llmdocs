"""
Results-related route handlers
"""
from flask import jsonify, request
import traceback
from pathlib import Path
from backend.services import EvaluatorService


def register_routes(app, socketio=None, running_benchmarks=None):
    """Register results routes"""

    TESTS_DIR = Path('tests')


    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """Get benchmark statistics"""
        try:
            from backend.services import EvaluatorService

            evaluator = EvaluatorService()
            tests = evaluator.tests

            total_tests = len(tests)
            total_points = sum(t['points'] for t in tests)

            level_stats = {}
            for level in range(1, 11):
                level_tests = [t for t in tests if t['level'] == level]
                level_stats[f'level_{level}'] = {
                    'count': len(level_tests),
                    'points': sum(t['points'] for t in level_tests)
                }

            category_stats = {}
            for test in tests:
                cat = test['category']
                if cat not in category_stats:
                    category_stats[cat] = {'count': 0, 'points': 0}
                category_stats[cat]['count'] += 1
                category_stats[cat]['points'] += test['points']

            return jsonify({
                'total_tests': total_tests,
                'total_points': total_points,
                'levels': level_stats,
                'categories': category_stats
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/compare', methods=['POST'])
    def compare_stashes():
        """Compare two stash directories"""
        try:
            data = request.json
            stash1 = data.get('stash1')
            stash2 = data.get('stash2')

            if not stash1 or not stash2:
                return jsonify({'error': 'Both stash1 and stash2 are required'}), 400

            dir1 = TESTS_DIR / stash1
            dir2 = TESTS_DIR / stash2

            if not dir1.exists() or not dir1.is_dir():
                return jsonify({'error': f'Stash not found: {stash1}'}), 404

            if not dir2.exists() or not dir2.is_dir():
                return jsonify({'error': f'Stash not found: {stash2}'}), 404

            def evaluate_directory(directory):
                test_files = list(directory.glob('*.txt'))
                scores = []
                category_data = {}

                for test_file in test_files:
                    evaluator = EvaluatorService()
                    result = evaluator.run_benchmark(str(test_file))

                    if result and result.get('summary') and 'error' not in result:
                        summary = result['summary']
                        overall_pct = summary.get('overall_percentage', 0)
                        scores.append(overall_pct)

                        breakdown = summary.get('category_breakdown', {})
                        for category, cat_data in breakdown.items():
                            if category not in category_data:
                                category_data[category] = []
                            category_data[category].append(cat_data.get('percentage', 0))

                avg_score = sum(scores) / len(scores) if scores else 0
                category_averages = {cat: sum(vals) / len(vals) for cat, vals in category_data.items()}

                return avg_score, scores, len(test_files), category_averages

            avg_score_1, scores_1, count_1, category_averages_1 = evaluate_directory(dir1)
            avg_score_2, scores_2, count_2, category_averages_2 = evaluate_directory(dir2)

            all_categories = set(category_averages_1.keys()) | set(category_averages_2.keys())

            files1 = [f.name for f in dir1.glob('*.txt')]
            files2 = [f.name for f in dir2.glob('*.txt')]

            return jsonify({
                'status': 'success',
                'stash1': {
                    'name': stash1,
                    'average_score': avg_score_1,
                    'scores': scores_1,
                    'file_count': count_1,
                    'category_averages': category_averages_1,
                    'filenames': files1
                },
                'stash2': {
                    'name': stash2,
                    'average_score': avg_score_2,
                    'scores': scores_2,
                    'file_count': count_2,
                    'category_averages': category_averages_2,
                    'filenames': files2
                },
                'all_categories': sorted(list(all_categories))
            })
        except Exception as e:
            app.logger.error(f'Error comparing stashes: {str(e)}')
            app.logger.error(traceback.format_exc())
            return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


