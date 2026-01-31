#!/usr/bin/env python3
"""Content validator for pipeline stages.

Validates that critical syntax patterns, code blocks, and content
are preserved between compression stages.
"""
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list
    missing_patterns: list
    size_ratio: float


@dataclass
class JacCheckResult:
    total_blocks: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    errors: list = field(default_factory=list)


class Validator:
    CRITICAL_PATTERNS = [
        (r'\+\+>', 'edge: ++>'),
        (r'<\+\+>', 'edge: <++>'),
        (r'-->', 'edge: -->'),
        (r'<-->', 'edge: <-->'),
        (r'by\s+llm\s*\(', 'by llm()'),
        (r'with\s+entry', 'with entry'),
        (r'with\s+exit', 'with exit'),
        (r'`root\s+entry', 'root entry'),
        (r'\bspawn\b', 'spawn'),
        (r'import\s+from\s+\w+\s*\{', 'import from module { }'),
        (r'\bhas\s+\w+\s*:', 'has x: type'),
        (r'\bnode\s+\w+', 'node definition'),
        (r'\bwalker\s+\w+', 'walker definition'),
        (r'\bedge\s+\w+', 'edge definition'),
        (r'\bobj\s+\w+', 'obj definition'),
        (r'\bcan\s+\w+', 'ability definition'),
        (r'file\.open', 'file.open'),
        (r'json\.dumps', 'json.dumps'),
        (r'json\.loads', 'json.loads'),
        (r'\basync\b', 'async'),
        (r'\bawait\b', 'await'),
        (r'\breport\b', 'report'),
        (r'\bvisit\b', 'visit'),
        (r'\bhere\b', 'here keyword'),
        (r'\bself\b', 'self keyword'),
        (r'\bprops\b', 'props keyword'),
        (r'\bcl\s*\{', 'client block'),
        (r'\bsv\s*\{', 'server block'),
        (r'<[A-Z]\w*', 'JSX element'),
        (r'/>', 'JSX self-closing'),
        (r'\buseState\b', 'React useState'),
        (r'\buseEffect\b', 'React useEffect'),
    ]

    def __init__(self, min_size_ratio=0.1, required_pattern_ratio=0.5):
        self.min_size_ratio = min_size_ratio
        self.required_pattern_ratio = required_pattern_ratio

    def find_patterns(self, text):
        found = set()
        for pattern, name in self.CRITICAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.add(name)
        return found

    def validate_code_blocks(self, text):
        fence_count = text.count('```')
        if fence_count % 2 != 0:
            return False, "Unbalanced code fences"
        return True, None

    def validate(self, input_text, output_text):
        issues = []
        missing_patterns = []

        if not output_text or not output_text.strip():
            return ValidationResult(
                is_valid=False,
                issues=["Output is empty"],
                missing_patterns=[],
                size_ratio=0.0
            )

        size_ratio = len(output_text) / max(len(input_text), 1)

        if size_ratio < self.min_size_ratio:
            issues.append(f"Output too small: {size_ratio:.1%} of input (min: {self.min_size_ratio:.0%})")

        valid_blocks, block_issue = self.validate_code_blocks(output_text)
        if not valid_blocks:
            issues.append(block_issue)

        input_patterns = self.find_patterns(input_text)
        output_patterns = self.find_patterns(output_text)

        if input_patterns:
            missing = input_patterns - output_patterns
            preserved_ratio = len(output_patterns) / len(input_patterns)

            if preserved_ratio < self.required_pattern_ratio:
                issues.append(
                    f"Too many patterns lost: {preserved_ratio:.0%} preserved "
                    f"(need {self.required_pattern_ratio:.0%})"
                )
            missing_patterns = list(missing)

        is_valid = len(issues) == 0
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            missing_patterns=missing_patterns,
            size_ratio=size_ratio
        )

    def validate_final(self, text, required_patterns=None):
        """Validate final output has minimum required patterns."""
        issues = []

        if required_patterns is None:
            required_patterns = [
                'edge: ++>', 'by llm()', 'with entry', 'spawn',
                'node definition', 'walker definition', 'has x: type'
            ]

        found = self.find_patterns(text)
        missing = [p for p in required_patterns if p not in found]

        if missing:
            issues.append(f"Missing required patterns: {missing}")

        valid_blocks, block_issue = self.validate_code_blocks(text)
        if not valid_blocks:
            issues.append(block_issue)

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            missing_patterns=missing,
            size_ratio=1.0
        )

    def extract_jac_blocks(self, text: str) -> list[tuple[int, str]]:
        """Extract Jac code blocks from markdown text.

        Returns list of (block_index, code) tuples.
        """
        blocks = []
        pattern = r'```(?:jac|jaclang)?\s*\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL | re.IGNORECASE)

        for i, match in enumerate(matches):
            code = match.group(1).strip()
            if code and not code.startswith('//') and len(code) > 10:
                blocks.append((i, code))

        return blocks

    def run_jac_check(self, code: str, timeout: int = 5) -> tuple[bool, Optional[str]]:
        """Run jac check on a code snippet.

        Returns (passed, error_message).
        """
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.jac', delete=False
        ) as f:
            f.write(code)
            f.flush()
            temp_path = Path(f.name)

        try:
            result = subprocess.run(
                ['jac', 'check', str(temp_path)],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return True, None
            else:
                error = result.stderr.strip() or result.stdout.strip()
                first_line = error.split('\n')[0] if error else "Unknown error"
                return False, first_line

        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except FileNotFoundError:
            return False, "jac CLI not found"
        except Exception as e:
            return False, str(e)
        finally:
            temp_path.unlink(missing_ok=True)

    def jac_check_examples(
        self,
        text: str,
        max_errors: int = 10,
        on_progress: Optional[callable] = None
    ) -> JacCheckResult:
        """Run jac check on all code examples in the documentation.

        Args:
            text: Documentation text containing code blocks
            max_errors: Maximum number of errors to collect
            on_progress: Optional callback(current, total, message)

        Returns:
            JacCheckResult with pass/fail statistics
        """
        blocks = self.extract_jac_blocks(text)
        total = len(blocks)
        passed = 0
        failed = 0
        skipped = 0
        errors = []

        for i, (block_idx, code) in enumerate(blocks):
            if on_progress:
                on_progress(i + 1, total, f"Checking block {block_idx + 1}...")

            # Skip blocks that are clearly partial/pseudocode
            if any(marker in code for marker in ['...', '# ...', '// ...']):
                skipped += 1
                continue

            # Skip very short snippets (likely incomplete)
            if len(code.split('\n')) < 2 and 'with entry' not in code:
                skipped += 1
                continue

            success, error = self.run_jac_check(code)

            if success:
                passed += 1
            else:
                failed += 1
                if len(errors) < max_errors:
                    preview = code[:100].replace('\n', ' ')
                    errors.append({
                        "block": block_idx + 1,
                        "error": error,
                        "preview": preview + "..." if len(code) > 100 else preview
                    })

        total_checked = passed + failed
        pass_rate = (passed / total_checked * 100) if total_checked > 0 else 0.0

        return JacCheckResult(
            total_blocks=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=pass_rate,
            errors=errors
        )
