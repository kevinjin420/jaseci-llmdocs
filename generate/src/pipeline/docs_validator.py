"""
Cross-reference validator against official Jac documentation.

Validates generated content patterns against the canonical Jac docs
to prevent hallucination of incorrect syntax.
"""
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DocsValidationResult:
    pattern: str
    found_in_docs: bool
    doc_file: str | None = None
    context: str | None = None


@dataclass
class SyntaxVerification:
    construct: str
    expected: str
    found_in_output: bool
    matches_docs: bool
    doc_example: str | None = None


class OfficialDocsValidator:
    """Cross-references generated content against official Jac docs."""

    OFFICIAL_DOCS_PATH = Path.home() / "jaseci/docs/docs/reference/language"

    CANONICAL_PATTERNS = {
        'spawn': {
            'correct': r'\w+\s+spawn\s+\w+\(',
            'wrong': r'\w+\(\)\s+spawn\s+\w+',
            'example': 'root spawn Walker();',
            'description': 'node first, then spawn Walker'
        },
        'connect': {
            'correct': r'\+>:\s*\w+',
            'wrong': None,
            'example': 'a +>: EdgeType() :+> b;',
            'description': 'edge connection with type'
        },
        'traverse': {
            'correct': r'\[-->:?\w*:?\]',
            'wrong': None,
            'example': '[-->:EdgeType:]',
            'description': 'typed edge traversal'
        },
        'tuple_unpack': {
            'correct': r'\(\s*\w+\s*,\s*\w+\s*\)\s*=',
            'wrong': r'(?<!\()[\w]+\s*,\s*[\w]+\s*=\s*\w+\s*\(',
            'example': '(a, b) = func();',
            'description': 'parentheses required for tuple unpacking'
        },
        'with_entry': {
            'correct': r'with\s+[`\w]+\s+entry',
            'wrong': None,
            'example': 'can action with `root entry { }',
            'description': 'with keyword required before entry'
        },
        'by_llm': {
            'correct': r'by\s+llm\s*[;(]',
            'wrong': None,
            'example': 'def func() -> str by llm;',
            'description': 'by llm; or by llm(args)'
        },
        'lambda': {
            'correct': r'lambda\s+\w+\s*:',
            'wrong': r'\|\w+\|\s*\{',
            'example': 'lambda x: int -> int { x * 2 }',
            'description': 'use lambda keyword, not |x| syntax'
        },
        'enumerate': {
            'correct': r'for\s+\(\s*\w+\s*,\s*\w+\s*\)\s+in\s+enumerate',
            'wrong': r'for\s+\w+\s*,\s*\w+\s+in\s+enumerate',
            'example': 'for (i, x) in enumerate(items) { }',
            'description': 'parentheses required for enumerate unpacking'
        },
    }

    def __init__(self):
        self.docs: dict[str, str] = {}
        self.official_examples: list[str] = []
        self._load_docs()

    def _load_docs(self) -> None:
        """Load all official doc markdown files."""
        if not self.OFFICIAL_DOCS_PATH.exists():
            return

        for md_file in self.OFFICIAL_DOCS_PATH.glob("*.md"):
            try:
                content = md_file.read_text()
                self.docs[md_file.stem] = content
                self.official_examples.extend(self._extract_code_blocks(content))
            except Exception:
                pass

    def _extract_code_blocks(self, text: str) -> list[str]:
        """Extract all jac code blocks from markdown text."""
        pattern = r'```(?:jac|jaclang)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [m.strip() for m in matches if m.strip()]

    def verify_pattern(self, pattern: str) -> DocsValidationResult:
        """Check if a syntax pattern exists in official docs."""
        for doc_name, content in self.docs.items():
            if pattern in content:
                start = content.find(pattern)
                context_start = max(0, start - 50)
                context_end = min(len(content), start + len(pattern) + 50)
                context = content[context_start:context_end]
                return DocsValidationResult(
                    pattern=pattern,
                    found_in_docs=True,
                    doc_file=doc_name,
                    context=context
                )

        return DocsValidationResult(
            pattern=pattern,
            found_in_docs=False
        )

    def validate_syntax_in_output(self, output: str) -> list[SyntaxVerification]:
        """Validate all critical syntax patterns in output against canonical patterns."""
        results = []
        cleaned_output = self._remove_wrong_examples(output)

        for construct, patterns in self.CANONICAL_PATTERNS.items():
            correct_pattern = patterns['correct']
            wrong_pattern = patterns['wrong']

            has_correct = bool(re.search(correct_pattern, cleaned_output))
            has_wrong = bool(re.search(wrong_pattern, cleaned_output)) if wrong_pattern else False

            doc_example = None
            for example in self.official_examples:
                if re.search(correct_pattern, example):
                    doc_example = example[:200]
                    break

            results.append(SyntaxVerification(
                construct=construct,
                expected=patterns['example'],
                found_in_output=has_correct or has_wrong,
                matches_docs=has_correct and not has_wrong,
                doc_example=doc_example
            ))

        return results

    def _remove_wrong_examples(self, text: str) -> str:
        """Remove wrong examples from text before validation."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            if line.strip().startswith('Wrong:'):
                continue
            line = re.split(r'[\s\(;]not\s', line)[0]
            cleaned.append(line)
        return '\n'.join(cleaned)

    def get_docs_summary(self) -> dict:
        """Get summary of loaded docs for debugging."""
        return {
            'docs_loaded': len(self.docs),
            'doc_files': list(self.docs.keys()),
            'total_examples': len(self.official_examples),
            'docs_path': str(self.OFFICIAL_DOCS_PATH),
            'docs_exist': self.OFFICIAL_DOCS_PATH.exists()
        }
