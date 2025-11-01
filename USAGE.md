# Jac LLM Benchmark - Usage Guide

## Quick Start

```bash
# 1. Export test cases
python3 jac_llm_benchmark.py export test_prompts.json

# 2. Give LLM these files:
#    - LLM_INSTRUCTIONS.md (instructions)
#    - jaseci-complete.txt (Jac documentation)
#    - test_prompts.json (test cases)

# 3. Save LLM's JSON response to: llm_responses.json

# 4. Evaluate
python3 jac_llm_benchmark.py evaluate llm_responses.json report.txt

# 5. View results
cat report.txt
```

## Commands

### Export Tests
```bash
python3 jac_llm_benchmark.py export <output.json>
```
Generates test cases JSON file for LLMs.

### Evaluate Responses
```bash
python3 jac_llm_benchmark.py evaluate <responses.json> [report.txt]
```
Scores LLM responses and generates report.

## Test Structure (40 tests, 900 points)

### Level 1: Basic Syntax (25 points)
- **basic_01** (5pts): Entry point with print statement
- **basic_02** (5pts): Global variable declaration and access
- **basic_03** (5pts): Enum declaration
- **basic_04** (5pts): Function with parameters and return type
- **basic_05** (5pts): For loop with range syntax

### Level 2: Objects (50 points)
- **obj_01** (10pts): Object with attributes
- **obj_02** (10pts): Object with method
- **obj_03** (10pts): Object inheritance
- **obj_04** (10pts): Object with postinit lifecycle method
- **obj_05** (10pts): Lambda function

### Level 3: Graph Basics (75 points)
- **graph_01** (15pts): Node declaration
- **graph_02** (15pts): Two nodes with bidirectional connection
- **graph_03** (15pts): Custom edge with properties
- **graph_04** (15pts): Node with entry ability
- **graph_05** (15pts): Node ability referencing visitor

### Level 4: Walkers (100 points)
- **walker_01** (20pts): Walker declaration with attributes
- **walker_02** (20pts): Walker with outgoing visit pattern
- **walker_03** (20pts): Walker with type filtering
- **walker_04** (20pts): Walker ability using 'here' reference
- **walker_05** (20pts): Walker using report statement

### Level 5: Advanced Graph (125 points)
- **advanced_01** (25pts): Walker with attribute filtering
- **advanced_02** (25pts): Walker with edge type filtering
- **advanced_03** (25pts): Multi-hop traversal (3 levels)
- **advanced_04** (25pts): Walker using disengage control
- **advanced_05** (25pts): Edge with entry ability

### Level 6: AI Integration (150 points)
- **ai_01** (30pts): Import Model from byllm
- **ai_02** (30pts): Global LLM model instance
- **ai_03** (30pts): AI function using 'by llm()'
- **ai_04** (30pts): Semantic string using 'sem' keyword
- **ai_05** (30pts): AI function returning enum type

### Level 7: Cloud (175 points)
- **cloud_01** (35pts): Walker with __specs__ for HTTP methods
- **cloud_02** (35pts): Walker disabling authentication
- **cloud_03** (35pts): Walker with custom path
- **cloud_04** (35pts): Walker with query parameters
- **cloud_05** (35pts): Private walker configuration

### Level 8: Integration (200 points)
- **integration_01** (40pts): Complete social graph with walker
- **integration_02** (40pts): State machine pattern
- **integration_03** (40pts): Error handling with try-except
- **integration_04** (40pts): Async function
- **integration_05** (40pts): CRUD walker with persistence

## Scoring

Each test evaluates:
1. **Required elements**: Specific syntax that must be present (main score)
2. **Forbidden elements**: Patterns to avoid (penalty)
3. **Syntax checks**: Semicolons, braces, type annotations (feedback only)

Score = (required_found / total_required) × points - penalties

## Grading Scale
- **90-100%** (810-900): Excellent
- **80-89%** (720-809): Good
- **70-79%** (630-719): Fair
- **60-69%** (540-629): Passing
- **<60%** (<540): Needs work

## Files

- **jac_llm_benchmark.py**: Main evaluation script
- **jaseci-complete.txt**: Jac language documentation (provide to LLM)
- **test_prompts.json**: Generated test cases (provide to LLM)
- **LLM_INSTRUCTIONS.md**: Instructions for LLM (provide to LLM)
- **example_responses.json**: Sample correct responses for testing

## Example LLM Prompt

```
You are being tested on Jac programming language.

INSTRUCTIONS:
[paste LLM_INSTRUCTIONS.md]

DOCUMENTATION:
[paste jaseci-complete.txt]

TEST CASES:
[paste test_prompts.json]

Respond with JSON mapping test IDs to Jac code.
```

## Testing the System

```bash
# Validate benchmark works
python3 jac_llm_benchmark.py evaluate example_responses.json test.txt
cat test.txt
```

## Output Files

- **report.txt**: Human-readable evaluation report with scores
- **responses_results.json**: Machine-readable detailed results

## Report Structure

```
OVERALL SUMMARY
- Total score and percentage
- Tests completed

CATEGORY BREAKDOWN
- Score by topic (Basic, Objects, Graph, Walkers, etc.)

LEVEL BREAKDOWN
- Score by difficulty (1-8)

DETAILED RESULTS
- Per-test score
- Required elements found/missing
- Syntax feedback
- Generated code
```

## Common Issues

**Low scores despite correct-looking code**
- Check required elements match exactly (case-sensitive)
- Verify Jac syntax (semicolons, braces, type annotations)
- Review hints for specific required patterns

**JSON validation errors**
- Check proper escaping: `\n` for newlines, `\"` for quotes
- Validate: `python3 -m json.tool responses.json`

**Missing tests in results**
- Ensure test IDs match exactly
- Verify all 40 tests have responses

## Comparing LLMs

```bash
# Test multiple models
python3 jac_llm_benchmark.py evaluate gpt4_responses.json gpt4_report.txt
python3 jac_llm_benchmark.py evaluate claude_responses.json claude_report.txt

# Compare
grep "overall_percentage" *_results.json
```
