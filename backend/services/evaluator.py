"""Code evaluation service for Jac benchmarks"""

import json
from pathlib import Path
from typing import Dict, List, Any

from ..utils.syntax import SyntaxChecker, patch_missing_braces


class EvaluatorService:
    """Service for evaluating Jac code against test requirements"""

    def __init__(self, tests_file: str = "tests.json"):
        """Initialize evaluator with test cases"""
        self.tests = self._load_test_cases(tests_file)

    def _load_test_cases(self, tests_file: str) -> List[Dict]:
        """Load test cases from JSON file"""
        tests_path = Path(tests_file)
        with open(tests_path, 'r') as f:
            return json.load(f)

    def evaluate_code(self, code: str, test_case: Dict) -> Dict:
        """Evaluate generated code against test requirements with strict validation"""
        score = 0
        max_score = test_case["points"]
        passed_checks = []
        failed_checks = []

        required_found = 0
        for element in test_case["required_elements"]:
            found = SyntaxChecker.validate_element_strict(code, element)
            if found:
                required_found += 1
                passed_checks.append(f"[PASS] Found required element: '{element}'")
            else:
                failed_checks.append(f"[FAIL] Missing required element: '{element}'")

        forbidden_found = 0
        for element in test_case["forbidden_elements"]:
            if element in code:
                forbidden_found += 1
                failed_checks.append(f"[FAIL] Contains forbidden element: '{element}'")
            else:
                passed_checks.append(f"[PASS] Correctly avoided: '{element}'")

        total_required = len(test_case["required_elements"])
        total_forbidden = len(test_case["forbidden_elements"])

        if total_required > 0:
            required_score = (required_found / total_required) * max_score
        else:
            required_score = max_score

        if total_forbidden > 0:
            forbidden_penalty = (forbidden_found / total_forbidden) * (max_score * 0.3)
        else:
            forbidden_penalty = 0

        score = max(0, required_score - forbidden_penalty)

        syntax_checks = SyntaxChecker.check_syntax(code)

        syntax_errors = len([c for c in syntax_checks if c.startswith('[WARN]')])
        syntax_penalty = min(syntax_errors * 0.10 * max_score, max_score * 0.50)
        score = max(0, score - syntax_penalty)

        return {
            "test_id": test_case["id"],
            "category": test_case["category"],
            "level": test_case["level"],
            "score": round(score, 2),
            "max_score": max_score,
            "percentage": round((score / max_score) * 100, 2),
            "required_found": f"{required_found}/{total_required}",
            "forbidden_found": forbidden_found,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "syntax_feedback": syntax_checks,
            "syntax_errors": syntax_errors,
            "code": code
        }

    def run_benchmark(self, responses_file: str) -> Dict:
        """Run benchmark on LLM responses from file"""
        try:
            with open(responses_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in '{responses_file}' at line {e.lineno}: {e.msg}")
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: '{responses_file}'")

        if "metadata" in data and "responses" in data:
            metadata = data["metadata"]
            responses = data["responses"]
        else:
            responses = data
            metadata = {}

        results = []
        category_scores = {}
        level_scores = {}
        patched_count = 0

        for test_case in self.tests:
            test_id = test_case["id"]
            if test_id in responses:
                code = responses[test_id]

                patched_code, was_patched = patch_missing_braces(code)
                if was_patched:
                    patched_count += 1

                result = self.evaluate_code(patched_code, test_case)
                result["was_patched"] = was_patched
                results.append(result)

                category = test_case["category"]
                if category not in category_scores:
                    category_scores[category] = {"score": 0, "max": 0, "count": 0}
                category_scores[category]["score"] += result["score"]
                category_scores[category]["max"] += result["max_score"]
                category_scores[category]["count"] += 1

                level = test_case["level"]
                if level not in level_scores:
                    level_scores[level] = {"score": 0, "max": 0, "count": 0}
                level_scores[level]["score"] += result["score"]
                level_scores[level]["max"] += result["max_score"]
                level_scores[level]["count"] += 1

        total_score = sum(r["score"] for r in results)
        total_max = sum(r["max_score"] for r in results)
        overall_percentage = (total_score / total_max * 100) if total_max > 0 else 0

        return {
            "results": results,
            "summary": {
                "total_score": round(total_score, 2),
                "total_max": total_max,
                "overall_percentage": round(overall_percentage, 2),
                "tests_completed": len(results),
                "tests_total": len(self.tests),
                "patched_count": patched_count,
                "category_breakdown": {
                    cat: {
                        "score": round(scores["score"], 2),
                        "max": scores["max"],
                        "percentage": round((scores["score"] / scores["max"] * 100) if scores["max"] > 0 else 0, 2),
                        "count": scores["count"]
                    }
                    for cat, scores in category_scores.items()
                },
                "level_breakdown": {
                    f"Level {level}": {
                        "score": round(scores["score"], 2),
                        "max": scores["max"],
                        "percentage": round((scores["score"] / scores["max"] * 100) if scores["max"] > 0 else 0, 2),
                        "count": scores["count"]
                    }
                    for level, scores in sorted(level_scores.items())
                }
            }
        }

    def evaluate_responses(self, responses: Dict[str, str]) -> Dict[str, Any]:
        """Evaluate a dictionary of test responses (for API use)"""
        results = []
        category_scores = {}
        level_scores = {}
        patched_count = 0

        for test_case in self.tests:
            test_id = test_case["id"]
            if test_id in responses:
                code = responses[test_id]

                patched_code, was_patched = patch_missing_braces(code)
                if was_patched:
                    patched_count += 1

                result = self.evaluate_code(patched_code, test_case)
                result["was_patched"] = was_patched
                results.append(result)

                category = test_case["category"]
                if category not in category_scores:
                    category_scores[category] = {"score": 0, "max": 0, "count": 0}
                category_scores[category]["score"] += result["score"]
                category_scores[category]["max"] += result["max_score"]
                category_scores[category]["count"] += 1

                level = test_case["level"]
                if level not in level_scores:
                    level_scores[level] = {"score": 0, "max": 0, "count": 0}
                level_scores[level]["score"] += result["score"]
                level_scores[level]["max"] += result["max_score"]
                level_scores[level]["count"] += 1

        total_score = sum(r["score"] for r in results)
        total_max = sum(r["max_score"] for r in results)
        overall_percentage = (total_score / total_max * 100) if total_max > 0 else 0

        return {
            "evaluation_results": {
                cat: {
                    "score": round(scores["score"], 2),
                    "max": scores["max"],
                    "percentage": round((scores["score"] / scores["max"] * 100) if scores["max"] > 0 else 0, 2),
                    "count": scores["count"],
                    "tests": [r for r in results if r["category"] == cat]
                }
                for cat, scores in category_scores.items()
            },
            "level_breakdown": {
                f"Level {level}": {
                    "score": round(scores["score"], 2),
                    "max": scores["max"],
                    "percentage": round((scores["score"] / scores["max"] * 100) if scores["max"] > 0 else 0, 2),
                    "count": scores["count"]
                }
                for level, scores in sorted(level_scores.items())
            },
            "total_score": round(total_score, 2),
            "max_score": total_max,
            "percentage": round(overall_percentage, 2),
            "tests_completed": len(results),
            "patched_count": patched_count
        }

    def get_test_stats(self) -> Dict[str, Any]:
        """Get statistics about test cases"""
        level_stats = {}
        category_stats = {}

        for test in self.tests:
            level = test['level']
            category = test['category']

            if level not in level_stats:
                level_stats[level] = {'count': 0, 'points': 0}
            level_stats[level]['count'] += 1
            level_stats[level]['points'] += test['points']

            if category not in category_stats:
                category_stats[category] = {'count': 0, 'points': 0}
            category_stats[category]['count'] += 1
            category_stats[category]['points'] += test['points']

        total_points = sum(t['points'] for t in self.tests)

        return {
            'total_tests': len(self.tests),
            'total_points': total_points,
            'levels': level_stats,
            'categories': category_stats
        }
