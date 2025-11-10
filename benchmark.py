#!/usr/bin/env python3
# Usage: ./benchmark.py [eval FILE | eval-all | gen | stats | compare DIR1 DIR2] - Jac language LLM benchmark suite

import json
import re
import sys
import glob
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
class JacBenchmark:
    """Benchmark suite for testing LLM Jac code generation"""

    def __init__(self):
        self.tests = self.load_test_cases()
        self.results = []

    def load_test_cases(self) -> List[Dict]:
        """Load test cases from external JSON file"""
        tests_file = Path(__file__).parent / "tests.json"
        with open(tests_file, 'r') as f:
            return json.load(f)

    def evaluate_code(self, code: str, test_case: Dict) -> Dict:
        """Evaluate generated code against test requirements"""
        score = 0
        max_score = test_case["points"]
        feedback = []
        passed_checks = []
        failed_checks = []

        # Check for required elements
        required_found = 0
        for element in test_case["required_elements"]:
            if element in code:
                required_found += 1
                passed_checks.append(f"✓ Found required element: '{element}'")
            else:
                failed_checks.append(f"✗ Missing required element: '{element}'")

        # Check for forbidden elements
        forbidden_found = 0
        for element in test_case["forbidden_elements"]:
            if element in code:
                forbidden_found += 1
                failed_checks.append(f"✗ Contains forbidden element: '{element}'")
            else:
                passed_checks.append(f"✓ Correctly avoided: '{element}'")

        # Calculate score
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

        # Additional syntax checks
        syntax_checks = self.check_syntax(code)
        feedback.extend(syntax_checks)

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
            "code": code
        }

    def check_syntax(self, code: str) -> List[str]:
        """Enhanced syntax validation checks for Jac code"""
        checks = []

        # Check for basic Jac syntax patterns
        if re.search(r'\bwith entry\b', code) and not re.search(r'with entry\s*{', code):
            checks.append("⚠ 'with entry' should be followed by a block { }")

        if re.search(r'\bwith exit\b', code) and not re.search(r'with exit\s*{', code):
            checks.append("⚠ 'with exit' should be followed by a block { }")

        # Check for proper braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            checks.append(f"⚠ Mismatched braces: {open_braces} opening, {close_braces} closing")

        # Check for brackets balance
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            checks.append(f"⚠ Mismatched brackets: {open_brackets} opening, {close_brackets} closing")

        # Check for parentheses balance
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            checks.append(f"⚠ Mismatched parentheses: {open_parens} opening, {close_parens} closing")

        # Check for semicolons
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('*#'):
                continue

            # Check if statement line needs semicolon
            needs_semi = any(keyword in stripped for keyword in [
                'glob ', 'has ', 'print(', 'report ', 'import ', 'include ',
                'disengage', 'raise ', 'return ', 'break', 'continue'
            ])

            # Lines that don't need semicolons
            no_semi_start = ('def ', 'obj ', 'node ', 'edge ', 'walker ', 'enum ',
                            'can ', 'if ', 'elif ', 'else', 'for ', 'while ',
                            'try', 'except', 'match ', 'case ', 'async def',
                            'with ', 'class ')
            no_semi_end = ('{', '}', ':', ',', '\\')

            # Assignment that's not in a declaration
            has_assignment = '=' in stripped and not stripped.startswith(no_semi_start)

            if (needs_semi or has_assignment) and not stripped.startswith(no_semi_start):
                if not stripped.endswith(no_semi_end) and not stripped.endswith(';'):
                    checks.append(f"⚠ Line {i} may be missing semicolon: {stripped[:60]}")

        # Check for type annotations on attributes
        if re.search(r'has\s+\w+\s*=', code) and not re.search(r'has\s+\w+\s*:\s*\w+', code):
            checks.append("⚠ Attributes should have type annotations (has name: type)")

        # Check for type annotations on function parameters
        if re.search(r'def\s+\w+\s*\([^)]*\w+\s*\)', code):
            if not re.search(r'def\s+\w+\s*\([^)]*:\s*\w+', code):
                checks.append("⚠ Function parameters should have type annotations")

        # Check for return type annotations
        if 'def ' in code and 'return' in code:
            if not re.search(r'def\s+\w+[^{]*->\s*\w+', code):
                checks.append("⚠ Functions with return statements should have return type annotations (-> type)")

        # Check for proper node/edge/walker syntax
        if re.search(r'\bnode\s+\w+\s+\w+', code):
            checks.append("⚠ Node declaration should use 'node ClassName {' syntax")

        if re.search(r'\bedge\s+\w+\s+\w+', code):
            checks.append("⚠ Edge declaration should use 'edge ClassName {' syntax")

        if re.search(r'\bwalker\s+\w+\s+\w+', code):
            checks.append("⚠ Walker declaration should use 'walker ClassName {' syntax")

        # Check for proper connection operators
        if '-->' in code and not any(op in code for op in ['[-->', '-->]', '++>', '+>:']):
            checks.append("⚠ Navigation operator '-->' should be used in visit statements with brackets")

        # Check for proper visit syntax
        if 'visit' in code and not re.search(r'visit\s+\[', code):
            checks.append("⚠ Visit statements should use bracket notation: visit [...]")

        # Check for proper global access
        if 'glob ' in code and ':g:' not in code:
            checks.append("⚠ Global variables should be accessed with :g: notation")

        # Check for proper backtick usage in filtering
        if '?' in code and '`?' not in code and 'visit' in code:
            checks.append("⚠ Type filtering in visit should use backtick: `?Type")

        # Check for spawn syntax
        if 'spawn' in code and not re.search(r'(root|here|\w+)\s+spawn\s+\w+', code):
            checks.append("⚠ Spawn should follow pattern: 'node spawn walker_instance'")

        # Check for ability syntax
        if 'can ' in code and 'with' in code:
            if not re.search(r'can\s+\w+\s+with\s+(entry|exit)', code):
                checks.append("⚠ Abilities should use 'can ability_name with entry/exit' syntax")

        # Check for proper AI function syntax
        if 'by llm(' in code and 'def' in code:
            if not re.search(r'def\s+\w+[^{]*by\s+llm\(\)', code):
                checks.append("⚠ AI functions should use 'def func() -> type by llm()' syntax")

        # Check for walker specs syntax
        if '__specs__' in code:
            if not re.search(r'obj\s+__specs__\s*{', code):
                checks.append("⚠ Walker specs should use 'obj __specs__ { static has ... }' syntax")

        # Check for import syntax
        if re.search(r'import\s+\w+\s*(?!;|from)', code):
            checks.append("⚠ Import statements should end with semicolon")

        # Check for proper edge connection syntax
        if any(op in code for op in ['++>', '<++>', '+>:', '<+:']):
            if not re.search(r'\w+\s*(-->|<-->|<--|\+\+>|<\+\+>|\+>:|<\+:)', code):
                checks.append("⚠ Connection operators should be used between nodes")

        # Provide positive feedback for good practices
        good_practices = []
        if re.search(r'has\s+\w+\s*:\s*\w+', code):
            good_practices.append("✓ Using type annotations on attributes")
        if re.search(r'def\s+\w+[^{]*->\s*\w+', code):
            good_practices.append("✓ Using return type annotations")
        if re.search(r'with entry\s*{', code):
            good_practices.append("✓ Proper entry block syntax")
        if re.search(r'visit\s+\[', code):
            good_practices.append("✓ Correct visit statement syntax")

        # Add good practices to checks (optional, for feedback)
        # checks.extend(good_practices)

        return checks

    def run_benchmark(self, responses_file: str) -> Dict:
        """Run benchmark on LLM responses from file"""
        # Load responses
        try:
            with open(responses_file, 'r') as f:
                responses = json.load(f)
        except json.JSONDecodeError as e:
            print(f"\n{'='*70}")
            print(f"ERROR: Invalid JSON in '{responses_file}'")
            print(f"{'='*70}")
            print(f"\nJSON Parsing Error at line {e.lineno}, column {e.colno} (character {e.pos}):")
            print(f"  {e.msg}")
            print(f"\nCommon causes:")
            print(f"  - Trailing comma after last entry (not allowed in JSON)")
            print(f"  - Missing quotes around property names")
            print(f"  - Unescaped quotes or newlines in strings")
            print(f"  - Invalid escape sequences")
            print(f"\nTo debug:")
            print(f"  1. Check line {e.lineno} in the file")
            print(f"  2. Look for trailing commas before closing braces")
            print(f"  3. Validate JSON with: python3 -m json.tool {responses_file}")
            print(f"\n{'='*70}\n")
            raise SystemExit(1)
        except FileNotFoundError:
            print(f"\n{'='*70}")
            print(f"ERROR: File not found: '{responses_file}'")
            print(f"{'='*70}\n")
            raise SystemExit(1)

        results = []
        category_scores = {}
        level_scores = {}

        for test_case in self.tests:
            test_id = test_case["id"]
            if test_id in responses:
                code = responses[test_id]
                result = self.evaluate_code(code, test_case)
                results.append(result)

                # Track category scores
                category = test_case["category"]
                if category not in category_scores:
                    category_scores[category] = {"score": 0, "max": 0, "count": 0}
                category_scores[category]["score"] += result["score"]
                category_scores[category]["max"] += result["max_score"]
                category_scores[category]["count"] += 1

                # Track level scores
                level = test_case["level"]
                if level not in level_scores:
                    level_scores[level] = {"score": 0, "max": 0, "count": 0}
                level_scores[level]["score"] += result["score"]
                level_scores[level]["max"] += result["max_score"]
                level_scores[level]["count"] += 1

        # Calculate summary statistics
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

    def generate_report(self, benchmark_results: Dict):
        """Generate summary report to stdout using Jinja template"""
        summary = benchmark_results["summary"]

        # Setup Jinja environment
        template_dir = Path(__file__).parent / 'templates'
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('single_eval.md.jinja')

        # Render and print
        output = template.render(summary=summary)
        print(output)

class MultiDocEvaluator:
    """Evaluates multiple documentation test results and generates comparison report"""

    VARIANTS = ['mini', 'slim', 'core', 'full']  # In increasing size order
    TESTS_DIR = Path('tests')
    REPORTS_DIR = TESTS_DIR / 'reports'
    RELEASE_DIR = Path('release')  # Original documentation files

    def __init__(self):
        self.results = {}
        self.file_sizes = {}
        # Create reports directory if it doesn't exist
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        if file_path.exists():
            return file_path.stat().st_size
        return 0

    def run_benchmark(self, variant: str) -> Dict:
        """Run benchmark for a specific variant"""
        file_name = f"test-llmdocs-jaseci-{variant}.txt"
        file_path = self.TESTS_DIR / file_name

        if not file_path.exists():
            print(f"Warning: {file_path} not found, skipping...")
            return None

        # Get file size from original documentation file in release/
        doc_file_name = f"llmdocs-jaseci-{variant}.txt"
        doc_file_path = self.RELEASE_DIR / doc_file_name
        file_size = self.get_file_size(doc_file_path)
        self.file_sizes[variant] = file_size

        # Run benchmark using jac_llm_benchmark.py
        print(f"Evaluating {variant}...")
        try:
            # Import and run benchmark directly to get structured results
            from jac_llm_benchmark import JacBenchmark
            benchmark = JacBenchmark()
            results = benchmark.run_benchmark(str(file_path))

            return results

        except json.JSONDecodeError as e:
            print(f"JSON error in {variant}: {e}")
            return None
        except Exception as e:
            print(f"Error evaluating {variant}: {e}")
            return None

    def check_all_files_exist(self) -> bool:
        """Check if all required test files exist"""
        missing = []
        for variant in self.VARIANTS:
            file_name = f"test-llmdocs-jaseci-{variant}.txt"
            file_path = self.TESTS_DIR / file_name
            if not file_path.exists():
                missing.append(variant)

        if missing:
            print("ERROR: Missing required test files:")
            for variant in missing:
                print(f"  - test-llmdocs-jaseci-{variant}.txt")
            print("\nAll four variants (core, full, mini, slim) must be present.")
            return False
        return True

    def evaluate_all(self):
        """Evaluate all variants"""
        print("=" * 80)
        print("MULTI-DOCUMENTATION EVALUATION")
        print("=" * 80)
        print()

        # Check all files exist first
        if not self.check_all_files_exist():
            sys.exit(1)

        for variant in self.VARIANTS:
            result = self.run_benchmark(variant)
            if result:
                self.results[variant] = result

        print()

    def generate_comparison_report(self):
        """Generate comprehensive comparison report"""
        if not self.results:
            print("No results to report")
            return

        print("=" * 80)
        print("COMPARATIVE ANALYSIS REPORT")
        print("=" * 80)
        print()

        # Summary Table
        print("SUMMARY TABLE")
        print("-" * 80)
        print(f"{'Variant':<12} {'Size (bytes)':<14} {'Score':<12} {'Max':<6} {'%':<8} {'Score/KB':<12}")
        print("-" * 80)

        summary_data = []
        for variant in self.VARIANTS:
            if variant in self.results:
                summary = self.results[variant]['summary']
                size = self.file_sizes[variant]
                score = summary['total_score']
                max_score = summary['total_max']
                percentage = summary['overall_percentage']
                score_per_kb = (score / (size / 1024)) if size > 0 else 0

                summary_data.append({
                    'variant': variant,
                    'size': size,
                    'score': score,
                    'max_score': max_score,
                    'percentage': percentage,
                    'score_per_kb': score_per_kb
                })

                print(f"{variant:<12} {size:<14} {score:<12.2f} {max_score:<6} {percentage:<8.2f} {score_per_kb:<12.2f}")

        print()

        # Efficiency Rankings
        print("EFFICIENCY RANKINGS (Score per KB)")
        print("-" * 80)
        ranked = sorted(summary_data, key=lambda x: x['score_per_kb'], reverse=True)
        for i, data in enumerate(ranked, 1):
            print(f"{i}. {data['variant']:<12} {data['score_per_kb']:>8.2f} score/KB "
                  f"({data['score']:.2f}/{data['max_score']} points, {data['size']} bytes)")
        print()

        # Absolute Score Rankings
        print("ABSOLUTE SCORE RANKINGS")
        print("-" * 80)
        ranked_score = sorted(summary_data, key=lambda x: x['score'], reverse=True)
        for i, data in enumerate(ranked_score, 1):
            print(f"{i}. {data['variant']:<12} {data['score']:>8.2f}/{data['max_score']} "
                  f"({data['percentage']:.2f}%)")
        print()

        # Category Comparison
        print("CATEGORY PERFORMANCE COMPARISON")
        print("-" * 80)

        # Get all categories
        categories = set()
        for variant in self.results:
            categories.update(self.results[variant]['summary']['category_breakdown'].keys())

        for category in sorted(categories):
            print(f"\n{category}:")
            print(f"  {'Variant':<12} {'Score':<12} {'Max':<6} {'%':<8}")
            for variant in self.VARIANTS:
                if variant in self.results:
                    cat_data = self.results[variant]['summary']['category_breakdown'].get(category)
                    if cat_data:
                        print(f"  {variant:<12} {cat_data['score']:<12.2f} "
                              f"{cat_data['max']:<6} {cat_data['percentage']:<8.2f}")

        print()

        # Level Comparison
        print("DIFFICULTY LEVEL COMPARISON")
        print("-" * 80)

        # Get all levels
        levels = set()
        for variant in self.results:
            levels.update(self.results[variant]['summary']['level_breakdown'].keys())

        for level in sorted(levels):
            print(f"\n{level}:")
            print(f"  {'Variant':<12} {'Score':<12} {'Max':<6} {'%':<8}")
            for variant in self.VARIANTS:
                if variant in self.results:
                    level_data = self.results[variant]['summary']['level_breakdown'].get(level)
                    if level_data:
                        print(f"  {variant:<12} {level_data['score']:<12.2f} "
                              f"{level_data['max']:<6} {level_data['percentage']:<8.2f}")

        print()

        # Size Analysis
        print("SIZE ANALYSIS")
        print("-" * 80)
        if self.file_sizes:
            total_size = sum(self.file_sizes.values())
            print(f"Total combined size: {total_size:,} bytes ({total_size/1024:.2f} KB)")
            print(f"\nSize distribution:")
            for variant in self.VARIANTS:
                if variant in self.file_sizes:
                    size = self.file_sizes[variant]
                    pct = (size / total_size * 100) if total_size > 0 else 0
                    print(f"  {variant:<12} {size:>8,} bytes ({pct:>5.1f}%)")

        print()

        # Best Performer Analysis
        print("BEST PERFORMER ANALYSIS")
        print("-" * 80)

        best_overall = max(summary_data, key=lambda x: x['score'])
        best_efficiency = max(summary_data, key=lambda x: x['score_per_kb'])
        smallest = min(summary_data, key=lambda x: x['size'])

        print(f"Highest Score:       {best_overall['variant']} ({best_overall['score']:.2f}/{best_overall['max_score']})")
        print(f"Most Efficient:      {best_efficiency['variant']} ({best_efficiency['score_per_kb']:.2f} score/KB)")
        print(f"Smallest Size:       {smallest['variant']} ({smallest['size']} bytes)")

        print()
        print("=" * 80)

        # Save detailed results to Markdown in reports directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.REPORTS_DIR / f"evaluation_report_{timestamp}.md"

        # Generate markdown report
        md_content = self.generate_markdown_report(summary_data, categories, levels)

        with open(output_file, 'w') as f:
            f.write(md_content)

        print(f"\nDetailed markdown report saved to: {output_file}")

        return timestamp

    def generate_markdown_report(self, summary_data: List[Dict], categories: set, levels: set) -> str:
        """Generate comprehensive markdown report using Jinja template"""
        # Setup Jinja environment
        template_dir = Path(__file__).parent / 'templates'
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('multi_eval_report.md.jinja')

        # Prepare data for template
        total_size = sum(self.file_sizes.values())
        ranked_efficiency = sorted(summary_data, key=lambda x: x['score_per_kb'], reverse=True)
        ranked_score = sorted(summary_data, key=lambda x: x['score'], reverse=True)
        best_overall = max(summary_data, key=lambda x: x['score'])
        best_efficiency = max(summary_data, key=lambda x: x['score_per_kb'])
        smallest = min(summary_data, key=lambda x: x['size'])

        # Render template
        return template.render(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            summary_data=summary_data,
            ranked_efficiency=ranked_efficiency,
            ranked_score=ranked_score,
            categories=categories,
            levels=levels,
            variants=self.VARIANTS,
            results=self.results,
            file_sizes=self.file_sizes,
            total_size=total_size,
            best_overall=best_overall,
            best_efficiency=best_efficiency,
            smallest=smallest
        )

    def archive_results(self, timestamp: str):
        """Move test results to timestamped archive directory"""
        archive_dir = self.TESTS_DIR / timestamp
        archive_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nArchiving test results to {archive_dir}/")

        for variant in self.VARIANTS:
            file_name = f"test-llmdocs-jaseci-{variant}.txt"
            src = self.TESTS_DIR / file_name
            dst = archive_dir / file_name

            if src.exists():
                src.rename(dst)
                print(f"  Moved {file_name}")

        print("Archive complete!")



def generate_test_prompts(output_file: str = "test_prompts.json"):
    """Generate test prompts JSON file for LLM testing"""
    benchmark = JacBenchmark()
    
    prompts = {
        "instructions": """
# Jac Language LLM Benchmark - Test Instructions

You are being tested on your ability to write Jac code based on documentation.
For each test case, write ONLY the Jac code that solves the task.

## Important Rules:
1. Write complete, syntactically correct Jac code
2. Follow all Jac syntax conventions (semicolons, braces, type annotations)
3. Do NOT include explanations or markdown - ONLY code
4. Each response should be valid Jac code that could run
5. Pay attention to required elements mentioned in hints

## Response Format:
Your response file should be a JSON object where:
- Keys are test IDs (e.g., "basic_01", "walker_03")
- Values are the Jac code as strings

Example format:
{
    "basic_01": "with entry {\\n    print(\\"Hello, Jac!\\");\\n}",
    "basic_02": "glob counter: int = 0;\\n\\nwith entry {\\n    print(:g:counter);\\n}"
}

## Test Cases:
""",
        "tests": [
            {
                "id": test["id"],
                "level": test["level"],
                "category": test["category"],
                "task": test["task"],
                "points": test["points"],
                "hints": test["hints"]
            }
            for test in benchmark.tests
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(prompts, f, indent=2)
    
    print(f"Generated test prompts: {output_file}")
    print(f"Total tests: {len(prompts['tests'])}")


def show_stats():
    """Show benchmark statistics"""
    benchmark = JacBenchmark()
    tests = benchmark.tests

    print(f'Total tests: {len(tests)}')
    print()
    print('Breakdown by level:')
    for level in range(1, 11):
        level_tests = [t for t in tests if t['level'] == level]
        total_points = sum(t['points'] for t in level_tests)
        print(f'  Level {level}: {len(level_tests)} tests, {total_points} points')

    print()
    print('Breakdown by category:')
    categories = {}
    for test in tests:
        cat = test['category']
        if cat not in categories:
            categories[cat] = {'count': 0, 'points': 0}
        categories[cat]['count'] += 1
        categories[cat]['points'] += test['points']

    for cat in sorted(categories.keys()):
        print(f'  {cat}: {categories[cat]["count"]} tests, {categories[cat]["points"]} points')

    print()
    total_points = sum(t['points'] for t in tests)
    print(f'Total possible points: {total_points}')


def parse_score_from_report(file_path: Path) -> Tuple[float | None, Dict[str, float]]:
    """
    Parses the total score and category scores from a benchmark report file.
    Returns: (total_score, category_scores_dict)
    """
    if not file_path.exists():
        return None, {}

    content = file_path.read_text()

    # Parse total score
    total_score = None
    match = re.search(r"Total Score:\s+([\d.]+)\/", content)
    if match:
        total_score = float(match.group(1))

    # Parse category scores
    category_scores = {}

    # Find the CATEGORY BREAKDOWN section
    category_section = re.search(
        r"CATEGORY BREAKDOWN\s*-+\s*(.*?)\s*(?:DIFFICULTY|=+)",
        content,
        re.DOTALL
    )

    if category_section:
        category_text = category_section.group(1)
        # Match lines like: "Basic Syntax          23.00/ 25 ( 92.0%) [5 tests]"
        category_matches = re.findall(
            r"([A-Za-z\s]+?)\s+(\d+\.?\d*)\/\s*(\d+)",
            category_text
        )

        for category_name, score, max_score in category_matches:
            category_name = category_name.strip()
            category_scores[category_name] = float(score)

    return total_score, category_scores


def get_average_score(directory: Path) -> Tuple[float, List[float], int, Dict[str, List[float]]]:
    """
    Finds all .txt files in a directory and calculates their average score.
    Returns: (average_score, list_of_scores, file_count, category_scores_by_category)
    """
    scores = []
    category_data = {}  # {category_name: [scores]}
    file_paths = glob.glob(str(directory / "*.txt"))

    if not file_paths:
        print(f"Warning: No .txt files found in directory: {directory}", file=sys.stderr)
        return 0.0, [], 0, {}

    for file_path in file_paths:
        total_score, category_scores = parse_score_from_report(Path(file_path))
        if total_score is not None:
            scores.append(total_score)

            # Collect category scores
            for category, score in category_scores.items():
                if category not in category_data:
                    category_data[category] = []
                category_data[category].append(score)

    if not scores:
        print(f"Warning: Could not parse any scores from files in: {directory}", file=sys.stderr)
        return 0.0, [], len(file_paths), {}

    return sum(scores) / len(scores), scores, len(file_paths), category_data


def compare_directories(dir1: Path, dir2: Path, dir1_label: str = "Directory 1", dir2_label: str = "Directory 2"):
    """
    Compares the average scores between two directories using Jinja template.
    """
    # Calculate average scores
    avg_score_1, scores_1, count_1, categories_1 = get_average_score(dir1)
    avg_score_2, scores_2, count_2, categories_2 = get_average_score(dir2)

    # Get all unique categories
    all_categories = set(categories_1.keys()) | set(categories_2.keys())

    # Calculate average scores per category
    category_averages_1 = {cat: sum(scores) / len(scores) for cat, scores in categories_1.items()}
    category_averages_2 = {cat: sum(scores) / len(scores) for cat, scores in categories_2.items()}

    # Setup Jinja environment
    template_dir = Path(__file__).parent / 'templates'
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('comparison.md.jinja')

    # Render and print
    output = template.render(
        dir1=dir1,
        dir2=dir2,
        label1=dir1_label,
        label2=dir2_label,
        count1=count_1,
        count2=count_2,
        scores1=scores_1,
        scores2=scores_2,
        avg1=avg_score_1,
        avg2=avg_score_2,
        all_categories=all_categories,
        category_averages_1=category_averages_1,
        category_averages_2=category_averages_2
    )
    print(output)


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Jac Language LLM Benchmark Suite")
        print()
        print("Usage:")
        print("  ./benchmark.py eval <file>       - Evaluate single test file")
        print("  ./benchmark.py eval-all          - Evaluate all variant test files")
        print("  ./benchmark.py gen               - Generate test_prompts.json")
        print("  ./benchmark.py stats             - Show benchmark statistics")
        print("  ./benchmark.py compare <d1> <d2> - Compare two result directories")
        print()
        print("Examples:")
        print("  ./benchmark.py eval tests/test-llmdocs-jaseci-core_v3.txt")
        print("  ./benchmark.py eval-all")
        print("  ./benchmark.py gen")
        print("  ./benchmark.py compare results1/ results2/")
        return
    
    command = sys.argv[1]
    
    if command == "eval":
        if len(sys.argv) < 3:
            print("Error: Please specify a responses file")
            print("Usage: ./benchmark.py eval <file>")
            return
        
        responses_file = sys.argv[2]
        if not Path(responses_file).exists():
            print(f"Error: File not found: {responses_file}")
            return
        
        print(f"Running benchmark on {responses_file}...")
        print()
        benchmark = JacBenchmark()
        results = benchmark.run_benchmark(responses_file)
        benchmark.generate_report(results)
    
    elif command == "eval-all":
        evaluator = MultiDocEvaluator()
        evaluator.evaluate_all()
        evaluator.generate_comparison_report()
    
    elif command == "gen":
        output = sys.argv[2] if len(sys.argv) > 2 else "test_prompts.json"
        generate_test_prompts(output)
    
    elif command == "stats":
        show_stats()

    elif command == "compare":
        if len(sys.argv) < 4:
            print("Error: Please specify two directories to compare")
            print("Usage: ./benchmark.py compare <dir1> <dir2> [--label1 NAME] [--label2 NAME]")
            return

        dir1 = Path(sys.argv[2])
        dir2 = Path(sys.argv[3])

        # Check for optional labels
        label1 = "Directory 1"
        label2 = "Directory 2"

        for i in range(4, len(sys.argv)):
            if sys.argv[i] == "--label1" and i + 1 < len(sys.argv):
                label1 = sys.argv[i + 1]
            elif sys.argv[i] == "--label2" and i + 1 < len(sys.argv):
                label2 = sys.argv[i + 1]

        if not dir1.exists() or not dir1.is_dir():
            print(f"Error: {dir1} is not a valid directory", file=sys.stderr)
            return

        if not dir2.exists() or not dir2.is_dir():
            print(f"Error: {dir2} is not a valid directory", file=sys.stderr)
            return

        compare_directories(dir1, dir2, label1, label2)

    else:
        print(f"Unknown command: {command}")
        print("Run './benchmark.py' without arguments for usage information")


if __name__ == "__main__":
    main()

