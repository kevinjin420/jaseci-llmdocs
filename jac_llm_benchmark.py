#!/usr/bin/env python3
"""
Jac Language LLM Benchmark
Tests LLM ability to write Jac code based on documentation
"""

import json
import re
import sys
from typing import Dict, List, Tuple
from pathlib import Path

class JacBenchmark:
    """Benchmark suite for testing LLM Jac code generation"""

    def __init__(self):
        self.tests = self.load_test_cases()
        self.results = []

    def load_test_cases(self) -> List[Dict]:
        """Define all test cases with increasing difficulty"""
        return [
            # Level 1: Basic Syntax (5 tests)
            {
                "id": "basic_01",
                "level": 1,
                "category": "Basic Syntax",
                "task": "Create a simple Jac program with an entry point that prints 'Hello, Jac!'",
                "required_elements": ["with entry", "print", ";"],
                "forbidden_elements": [],
                "points": 5,
                "hints": ["Entry point syntax", "Statement termination"]
            },
            {
                "id": "basic_02",
                "level": 1,
                "category": "Basic Syntax",
                "task": "Declare a global variable named 'counter' of type int with value 0, then print it",
                "required_elements": ["glob", "counter", ": int", "= 0", ":g:"],
                "forbidden_elements": [],
                "points": 5,
                "hints": ["Global variable declaration", "Global access syntax"]
            },
            {
                "id": "basic_03",
                "level": 1,
                "category": "Basic Syntax",
                "task": "Create an enum called Status with values PENDING, ACTIVE, COMPLETED",
                "required_elements": ["enum Status", "PENDING", "ACTIVE", "COMPLETED"],
                "forbidden_elements": [],
                "points": 5,
                "hints": ["Enum syntax"]
            },
            {
                "id": "basic_04",
                "level": 1,
                "category": "Basic Syntax",
                "task": "Write a function named 'add_numbers' that takes two int parameters and returns their sum",
                "required_elements": ["def add_numbers", "int", "->", "return"],
                "forbidden_elements": [],
                "points": 5,
                "hints": ["Function definition", "Type annotations", "Return type"]
            },
            {
                "id": "basic_05",
                "level": 1,
                "category": "Basic Syntax",
                "task": "Create a for loop that iterates from 1 to 5 and prints each number",
                "required_elements": ["for", "to", "by", "{", "}"],
                "forbidden_elements": [],
                "points": 5,
                "hints": ["Jac for loop syntax with 'to' and 'by'"]
            },

            # Level 2: Objects & Types (5 tests)
            {
                "id": "obj_01",
                "level": 2,
                "category": "Objects",
                "task": "Create an object class named 'Person' with attributes name (str) and age (int)",
                "required_elements": ["obj Person", "has name: str", "has age: int"],
                "forbidden_elements": [],
                "points": 10,
                "hints": ["Object declaration", "Attribute declaration with 'has'"]
            },
            {
                "id": "obj_02",
                "level": 2,
                "category": "Objects",
                "task": "Create an object 'Car' with attributes brand (str), year (int), and a method 'get_info' that returns a formatted string",
                "required_elements": ["obj Car", "has brand", "has year", "def get_info", "return"],
                "forbidden_elements": [],
                "points": 10,
                "hints": ["Object with methods", "self reference"]
            },
            {
                "id": "obj_03",
                "level": 2,
                "category": "Objects",
                "task": "Create an object 'Student' that inherits from 'Person' and adds a 'grade' attribute",
                "required_elements": ["obj Student", "Person", "has grade"],
                "forbidden_elements": [],
                "points": 10,
                "hints": ["Inheritance syntax"]
            },
            {
                "id": "obj_04",
                "level": 2,
                "category": "Objects",
                "task": "Create an object with a postinit method that prints 'Object initialized'",
                "required_elements": ["obj", "def postinit", "print"],
                "forbidden_elements": [],
                "points": 10,
                "hints": ["Postinit lifecycle method"]
            },
            {
                "id": "obj_05",
                "level": 2,
                "category": "Objects",
                "task": "Create a lambda function that takes a number and returns its square",
                "required_elements": ["lambda", ":", "return"],
                "forbidden_elements": [],
                "points": 10,
                "hints": ["Lambda syntax with type annotations"]
            },

            # Level 3: Nodes & Edges (5 tests)
            {
                "id": "graph_01",
                "level": 3,
                "category": "Graph Basics",
                "task": "Create a node named 'City' with attributes name (str) and population (int)",
                "required_elements": ["node City", "has name: str", "has population: int"],
                "forbidden_elements": [],
                "points": 15,
                "hints": ["Node declaration syntax"]
            },
            {
                "id": "graph_02",
                "level": 3,
                "category": "Graph Basics",
                "task": "Create two City nodes and connect them with a bidirectional edge",
                "required_elements": ["node City", "City(", "<++>"],
                "forbidden_elements": [],
                "points": 15,
                "hints": ["Node instantiation", "Bidirectional connection operator"]
            },
            {
                "id": "graph_03",
                "level": 3,
                "category": "Graph Basics",
                "task": "Create a custom edge named 'Road' with attribute distance (float), then connect two cities with it",
                "required_elements": ["edge Road", "has distance", "+>:Road", ":+>"],
                "forbidden_elements": [],
                "points": 15,
                "hints": ["Edge declaration", "Typed edge connection"]
            },
            {
                "id": "graph_04",
                "level": 3,
                "category": "Graph Basics",
                "task": "Create a node with an ability that executes on entry",
                "required_elements": ["node", "can", "with entry"],
                "forbidden_elements": [],
                "points": 15,
                "hints": ["Node abilities", "Entry trigger"]
            },
            {
                "id": "graph_05",
                "level": 3,
                "category": "Graph Basics",
                "task": "Create a node that references 'visitor' in its ability to access the visiting walker",
                "required_elements": ["node", "can", "visitor"],
                "forbidden_elements": [],
                "points": 15,
                "hints": ["Node ability context", "Visitor reference"]
            },

            # Level 4: Walkers (5 tests)
            {
                "id": "walker_01",
                "level": 4,
                "category": "Walkers",
                "task": "Create a walker named 'Explorer' with an attribute visited_count (int) initialized to 0",
                "required_elements": ["walker Explorer", "has visited_count: int", "= 0"],
                "forbidden_elements": [],
                "points": 20,
                "hints": ["Walker declaration", "Attribute initialization"]
            },
            {
                "id": "walker_02",
                "level": 4,
                "category": "Walkers",
                "task": "Create a walker that visits all outgoing nodes using visit [-->]",
                "required_elements": ["walker", "visit", "[-->]"],
                "forbidden_elements": [],
                "points": 20,
                "hints": ["Walker visit syntax", "Outgoing edge pattern"]
            },
            {
                "id": "walker_03",
                "level": 4,
                "category": "Walkers",
                "task": "Create a walker that visits nodes filtered by type, using the ?Type syntax",
                "required_elements": ["walker", "visit", "`?"],
                "forbidden_elements": [],
                "points": 20,
                "hints": ["Type filtering in visit", "Backtick question mark syntax"]
            },
            {
                "id": "walker_04",
                "level": 4,
                "category": "Walkers",
                "task": "Create a walker with an entry ability that prints the current node using 'here'",
                "required_elements": ["walker", "can", "with entry", "here"],
                "forbidden_elements": [],
                "points": 20,
                "hints": ["Walker abilities", "Here reference for current location"]
            },
            {
                "id": "walker_05",
                "level": 4,
                "category": "Walkers",
                "task": "Create a walker that uses 'report' to stream a value back to the caller",
                "required_elements": ["walker", "report"],
                "forbidden_elements": [],
                "points": 20,
                "hints": ["Report statement for returning values"]
            },

            # Level 5: Advanced Graph Operations (5 tests)
            {
                "id": "advanced_01",
                "level": 5,
                "category": "Advanced Graph",
                "task": "Create a walker that filters nodes by an attribute value (e.g., ?attr == value)",
                "required_elements": ["walker", "visit", "?", "=="],
                "forbidden_elements": [],
                "points": 25,
                "hints": ["Attribute filtering syntax in visit statements"]
            },
            {
                "id": "advanced_02",
                "level": 5,
                "category": "Advanced Graph",
                "task": "Create a walker that filters by edge type using ->:EdgeType:->",
                "required_elements": ["walker", "visit", "->:", ":->"],
                "forbidden_elements": [],
                "points": 25,
                "hints": ["Edge type filtering"]
            },
            {
                "id": "advanced_03",
                "level": 5,
                "category": "Advanced Graph",
                "task": "Create a multi-hop traversal that goes 3 levels deep (node --> --> -->)",
                "required_elements": ["walker", "visit", "-->", "-->", "-->"],
                "forbidden_elements": [],
                "points": 25,
                "hints": ["Multi-hop traversal syntax"]
            },
            {
                "id": "advanced_04",
                "level": 5,
                "category": "Advanced Graph",
                "task": "Create a walker that uses 'disengage' to exit early",
                "required_elements": ["walker", "disengage"],
                "forbidden_elements": [],
                "points": 25,
                "hints": ["Walker control flow with disengage"]
            },
            {
                "id": "advanced_05",
                "level": 5,
                "category": "Advanced Graph",
                "task": "Create edge with an ability that triggers on walker entry",
                "required_elements": ["edge", "can", "with", "entry"],
                "forbidden_elements": [],
                "points": 25,
                "hints": ["Edge abilities"]
            },

            # Level 6: AI Integration (5 tests)
            {
                "id": "ai_01",
                "level": 6,
                "category": "AI Integration",
                "task": "Import Model from byllm module",
                "required_elements": ["import", "from byllm", "Model"],
                "forbidden_elements": [],
                "points": 30,
                "hints": ["Import syntax for byllm"]
            },
            {
                "id": "ai_02",
                "level": 6,
                "category": "AI Integration",
                "task": "Create a global LLM model instance with model name 'gpt-4o-mini'",
                "required_elements": ["glob", "Model", "model_name", "gpt-4o-mini"],
                "forbidden_elements": [],
                "points": 30,
                "hints": ["Model initialization"]
            },
            {
                "id": "ai_03",
                "level": 6,
                "category": "AI Integration",
                "task": "Create an AI function using 'by llm()' that generates a greeting",
                "required_elements": ["def", "by llm()", "->"],
                "forbidden_elements": [],
                "points": 30,
                "hints": ["AI function syntax with by keyword"]
            },
            {
                "id": "ai_04",
                "level": 6,
                "category": "AI Integration",
                "task": "Create a semantic string using 'sem' keyword to describe an attribute",
                "required_elements": ["sem", "="],
                "forbidden_elements": [],
                "points": 30,
                "hints": ["Semantic annotation syntax"]
            },
            {
                "id": "ai_05",
                "level": 6,
                "category": "AI Integration",
                "task": "Create an AI function that returns an enum type to constrain LLM output",
                "required_elements": ["enum", "def", "by llm()", "->"],
                "forbidden_elements": [],
                "points": 30,
                "hints": ["Enum as return type for AI functions"]
            },

            # Level 7: Cloud Deployment (5 tests)
            {
                "id": "cloud_01",
                "level": 7,
                "category": "Cloud",
                "task": "Create a walker with __specs__ that allows GET and POST methods",
                "required_elements": ["walker", "__specs__", "static has methods", "get", "post"],
                "forbidden_elements": [],
                "points": 35,
                "hints": ["Walker specs configuration", "HTTP methods"]
            },
            {
                "id": "cloud_02",
                "level": 7,
                "category": "Cloud",
                "task": "Create a walker that disables authentication using __specs__",
                "required_elements": ["walker", "__specs__", "static has auth: bool", "False"],
                "forbidden_elements": [],
                "points": 35,
                "hints": ["Auth configuration in specs"]
            },
            {
                "id": "cloud_03",
                "level": 7,
                "category": "Cloud",
                "task": "Create a walker with a custom path in __specs__",
                "required_elements": ["walker", "__specs__", "static has path: str"],
                "forbidden_elements": [],
                "points": 35,
                "hints": ["Custom endpoint path"]
            },
            {
                "id": "cloud_04",
                "level": 7,
                "category": "Cloud",
                "task": "Create a walker that marks all parameters as query params using as_query",
                "required_elements": ["walker", "__specs__", "static has as_query", "*"],
                "forbidden_elements": [],
                "points": 35,
                "hints": ["Query parameter configuration"]
            },
            {
                "id": "cloud_05",
                "level": 7,
                "category": "Cloud",
                "task": "Create a private walker that won't auto-generate an endpoint",
                "required_elements": ["walker", "__specs__", "static has private: bool", "True"],
                "forbidden_elements": [],
                "points": 35,
                "hints": ["Private walker configuration"]
            },

            # Level 8: Integration & Patterns (5 tests)
            {
                "id": "integration_01",
                "level": 8,
                "category": "Integration",
                "task": "Create a complete graph with Person nodes, Friendship edges, and a walker to traverse",
                "required_elements": ["node Person", "edge", "walker", "visit", "spawn"],
                "forbidden_elements": [],
                "points": 40,
                "hints": ["Complete social graph pattern"]
            },
            {
                "id": "integration_02",
                "level": 8,
                "category": "Integration",
                "task": "Create a state machine using nodes for states and a walker for transitions",
                "required_elements": ["node", "walker", "visit", "if"],
                "forbidden_elements": [],
                "points": 40,
                "hints": ["State machine pattern"]
            },
            {
                "id": "integration_03",
                "level": 8,
                "category": "Integration",
                "task": "Create error handling with try-except in a walker",
                "required_elements": ["walker", "try", "except", "as"],
                "forbidden_elements": [],
                "points": 40,
                "hints": ["Exception handling"]
            },
            {
                "id": "integration_04",
                "level": 8,
                "category": "Integration",
                "task": "Create an async function using async/await",
                "required_elements": ["async def", "await"],
                "forbidden_elements": [],
                "points": 40,
                "hints": ["Async syntax"]
            },
            {
                "id": "integration_05",
                "level": 8,
                "category": "Integration",
                "task": "Create a complete CRUD walker with create, read, update, delete operations",
                "required_elements": ["walker", "def", "save", "root"],
                "forbidden_elements": [],
                "points": 40,
                "hints": ["CRUD pattern with persistence"]
            }
        ]

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
        """Basic syntax validation checks"""
        checks = []

        # Check for basic Jac syntax patterns
        if re.search(r'\bwith entry\b', code) and not re.search(r'with entry\s*{', code):
            checks.append("⚠ 'with entry' should be followed by a block { }")

        # Check for semicolons
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('*#'):
                # Check if statement line needs semicolon
                if any(keyword in line for keyword in ['glob ', 'has ', '= ', 'print(', 'report ']):
                    if not line.endswith((';', '{', '}')) and not line.startswith(('def ', 'obj ', 'node ', 'edge ', 'walker ', 'enum ', 'can ')):
                        checks.append(f"⚠ Line {i} may be missing semicolon: {line[:50]}")

        # Check for type annotations
        if re.search(r'has \w+(?!:)', code):
            checks.append("⚠ Attributes should have type annotations (has name: type)")

        # Check for proper braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            checks.append(f"⚠ Mismatched braces: {open_braces} opening, {close_braces} closing")

        return checks

    def run_benchmark(self, responses_file: str) -> Dict:
        """Run benchmark on LLM responses from file"""
        # Load responses
        with open(responses_file, 'r') as f:
            responses = json.load(f)

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
        """Generate summary report to stdout"""
        summary = benchmark_results["summary"]

        print("=" * 80)
        print("JAC LANGUAGE LLM BENCHMARK REPORT")
        print("=" * 80)
        print()
        print("OVERALL SUMMARY")
        print("-" * 80)
        print(f"Total Score:      {summary['total_score']}/{summary['total_max']} ({summary['overall_percentage']}%)")
        print(f"Tests Completed:  {summary['tests_completed']}/{summary['tests_total']}")
        print()

        print("CATEGORY BREAKDOWN")
        print("-" * 80)
        for category, scores in summary["category_breakdown"].items():
            print(f"{category:20s} {scores['score']:6.2f}/{scores['max']:3d} ({scores['percentage']:5.1f}%) [{scores['count']} tests]")
        print()

        print("DIFFICULTY LEVEL BREAKDOWN")
        print("-" * 80)
        for level, scores in summary["level_breakdown"].items():
            print(f"{level:15s} {scores['score']:6.2f}/{scores['max']:3d} ({scores['percentage']:5.1f}%) [{scores['count']} tests]")
        print()
        print("=" * 80)

    def export_test_prompts(self, output_file: str):
        """Export test prompts for LLMs"""
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
            "tests": []
        }

        for test in self.tests:
            prompts["tests"].append({
                "id": test["id"],
                "level": test["level"],
                "category": test["category"],
                "task": test["task"],
                "points": test["points"],
                "hints": test["hints"]
            })

        with open(output_file, 'w') as f:
            json.dump(prompts, f, indent=2)

        print(f"Test prompts exported to {output_file}")
        print(f"Total tests: {len(self.tests)}")
        print(f"Total possible points: {sum(t['points'] for t in self.tests)}")


def main():
    """Main execution"""
    benchmark = JacBenchmark()

    if len(sys.argv) < 2:
        print("Jac Language LLM Benchmark")
        print("\nUsage:")
        print("  python jac_llm_benchmark.py export <output_file>")
        print("      Export test prompts for LLMs")
        print("\n  python jac_llm_benchmark.py evaluate <responses_file>")
        print("      Evaluate LLM responses (outputs to stdout)")
        print("\nExample:")
        print("  python jac_llm_benchmark.py export test_prompts.json")
        print("  python jac_llm_benchmark.py evaluate llm_responses.json")
        return

    command = sys.argv[1]

    if command == "export":
        if len(sys.argv) < 3:
            print("Error: Please specify output file")
            print("Usage: python jac_llm_benchmark.py export <output_file>")
            return

        output_file = sys.argv[2]
        benchmark.export_test_prompts(output_file)

    elif command == "evaluate":
        if len(sys.argv) < 3:
            print("Error: Please specify responses file")
            print("Usage: python jac_llm_benchmark.py evaluate <responses_file>")
            return

        responses_file = sys.argv[2]

        if not Path(responses_file).exists():
            print(f"Error: Responses file not found: {responses_file}")
            return

        print(f"Running benchmark on {responses_file}...")
        print()
        results = benchmark.run_benchmark(responses_file)
        benchmark.generate_report(results)

    else:
        print(f"Unknown command: {command}")
        print("Valid commands: export, evaluate")


if __name__ == "__main__":
    main()
