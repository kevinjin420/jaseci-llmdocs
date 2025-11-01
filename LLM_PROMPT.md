# Jac Language Coding Test

## Task
Write valid Jac code for each test case below. Return responses as JSON.

## Documentation
See `jaseci-jacbook.txt` and only this .txt in llmdocs/ for complete Jac language reference.

## Response Format
Return JSON object mapping test IDs to code strings:

```json
{
    "basic_01": "with entry {\n    print(\"Hello, Jac!\");\n}",
    "basic_02": "glob counter: int = 0;\n\nwith entry {\n    print(:g:counter);\n}",
    "obj_01": "obj Person {\n    has name: str;\n    has age: int;\n}"
}
```
Output to "test-<documentation name>.txt"

## Test Cases
See `test_prompts.json` for all 40 test cases with:
- `id`: Test identifier (use as JSON key)
- `task`: What to implement
- `hints`: Required elements to include
- `points`: Point value

## Important
- Write ONLY valid Jac code, no explanations
- Include all required elements from hints
- Use proper Jac syntax (not Python syntax)
- Escape strings properly in JSON (`\n` for newlines, `\"` for quotes)
- Respond with all 40 tests
