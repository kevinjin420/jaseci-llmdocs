#!/usr/bin/env python3
"""Content validator for pipeline stages.

Validates that critical syntax patterns, code blocks, and content
are preserved between compression stages.
"""
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Optional


class ValidationError(Exception):
    """Raised when strict validation fails."""
    pass


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

    def extract_inline_jac(self, text: str) -> list[tuple[int, str, str]]:
        """Extract Jac code blocks from plaintext inline format.

        Returns list of (line_number, code, category) tuples.
        Line numbers are 1-indexed (matching file line numbers).
        Categories: 'definition', 'example', 'entry_point'
        """
        lines = text.split('\n')
        blocks = []

        definition_keywords = (
            'node ', 'walker ', 'edge ', 'obj ', 'enum ',
            'async walker ', 'async def '
        )

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line or line.startswith('#') or line.startswith('//'):
                i += 1
                continue

            if ':' in line and '{' not in line and not any(
                line.startswith(kw) for kw in definition_keywords
            ):
                i += 1
                continue

            code = None
            category = None
            start_line = i + 1  # 1-indexed line number

            if any(line.startswith(kw) for kw in definition_keywords):
                code, end_line = self._extract_balanced_block(lines, i)
                category = 'definition'
                i = end_line + 1
            elif line.startswith('with entry') or line.startswith('with exit'):
                code, end_line = self._extract_balanced_block(lines, i)
                category = 'entry_point'
                i = end_line + 1
            elif line.startswith('def ') and '{' in line:
                code, end_line = self._extract_balanced_block(lines, i)
                category = 'definition'
                i = end_line + 1
            else:
                i += 1
                continue

            if code and len(code) > 15:
                open_count = code.count('{')
                close_count = code.count('}')
                if open_count == close_count and open_count > 0:
                    blocks.append((start_line, code, category))

        return blocks

    def _extract_balanced_block(
        self, lines: list[str], start_idx: int
    ) -> tuple[str, int]:
        """Extract a code block with balanced braces starting at start_idx."""
        result_lines = []
        brace_count = 0
        started = False
        end_idx = start_idx

        for i in range(start_idx, len(lines)):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                if started and brace_count == 0:
                    break
                if started:
                    result_lines.append(line)
                continue

            if stripped.startswith('#') and not started:
                break

            for char in stripped:
                if char == '{':
                    brace_count += 1
                    started = True
                elif char == '}':
                    brace_count -= 1

            result_lines.append(stripped)
            end_idx = i

            if started and brace_count == 0:
                break

        return ' '.join(result_lines), end_idx

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

    def _is_fragment(self, code: str) -> bool:
        """Check if code is a fragment (incomplete snippet) that shouldn't be validated."""
        lines = code.strip().split('\n')
        if len(lines) < 2:
            if 'with entry' not in code and 'spawn' not in code:
                return True

        fragment_markers = ['...', '# ...', '// ...', '/* ... */', '...}', '{...']
        if any(marker in code for marker in fragment_markers):
            return True

        has_definition = any(
            re.search(pattern, code)
            for pattern in [r'\bnode\s+\w+', r'\bwalker\s+\w+', r'\bedge\s+\w+',
                            r'\bobj\s+\w+', r'\bdef\s+\w+', r'\bcan\s+\w+',
                            r'with\s+.*entry', r'with\s+.*exit']
        )
        if not has_definition and len(lines) < 3:
            return True

        return False

    def _check_block_task(
        self,
        idx: int,
        code: str,
        source: str
    ) -> tuple[int, str, str, Optional[bool], Optional[str]]:
        """Task for thread pool - check a single code block.

        Returns (idx, code, source, success, error).
        success=None indicates the block was skipped.
        """
        if self._is_fragment(code):
            return (idx, code, source, None, None)

        success, error = self.run_jac_check(code)
        return (idx, code, source, success, error)

    def validate_all_examples(
        self,
        text: str,
        fail_threshold: float = 90.0,
        on_progress: Optional[callable] = None,
        max_workers: Optional[int] = None
    ) -> JacCheckResult:
        """Run jac check on all fenced code blocks using parallel processing.

        Args:
            text: Documentation text containing code blocks
            fail_threshold: Minimum pass rate percentage (default 90%)
            on_progress: Optional callback(current, total, message)
            max_workers: Maximum threads (default: min(32, cpu_count * 2))

        Returns:
            JacCheckResult with comprehensive statistics
        """
        blocks = self.extract_jac_blocks(text)
        total = len(blocks)

        if total == 0:
            return JacCheckResult(0, 0, 0, 0, 0.0, [])

        if max_workers is None:
            max_workers = min(32, (os.cpu_count() or 4) * 2)

        passed = 0
        failed = 0
        skipped = 0
        errors = []
        completed = 0
        progress_lock = Lock()

        def update_progress():
            nonlocal completed
            with progress_lock:
                completed += 1
                if on_progress:
                    on_progress(completed, total, f"Validating {completed}/{total} blocks")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._check_block_task, block_idx, code, 'fenced'): (block_idx, code)
                for block_idx, code in blocks
            }

            for future in as_completed(futures):
                block_idx, code, _, success, error = future.result()
                update_progress()

                if success is None:
                    skipped += 1
                elif success:
                    passed += 1
                else:
                    failed += 1
                    preview = code[:150].replace('\n', ' ')
                    errors.append({
                        "block": block_idx + 1,
                        "error": error,
                        "code_preview": preview + "..." if len(code) > 150 else preview
                    })

        total_checked = passed + failed
        pass_rate = (passed / total_checked * 100) if total_checked > 0 else 0.0

        result = JacCheckResult(
            total_blocks=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=pass_rate,
            errors=errors
        )

        if pass_rate < fail_threshold and total_checked > 0:
            print(f"WARNING: Only {pass_rate:.1f}% of examples passed jac check (threshold: {fail_threshold}%)")
            for err in errors[:5]:
                print(f"  Block {err['block']}: {err['error']}")

        return result

    def validate_strict(
        self,
        text: str,
        fail_on_error: bool = True,
        on_progress: Optional[callable] = None,
        max_workers: Optional[int] = None
    ) -> JacCheckResult:
        """Strictly validate ALL Jac code using parallel processing.

        Extracts code from markdown fences AND inline plaintext format,
        then runs jac check on each block in parallel using ThreadPoolExecutor.

        Args:
            text: Documentation text containing code blocks
            fail_on_error: If True, raise ValidationError on any failure
            on_progress: Optional callback(current, total, message)
            max_workers: Maximum threads (default: min(32, cpu_count * 2))

        Returns:
            JacCheckResult with comprehensive statistics

        Raises:
            ValidationError: If fail_on_error=True and any block fails
        """
        fenced_blocks = self.extract_jac_blocks(text)
        inline_blocks = self.extract_inline_jac(text)

        all_blocks = []
        for idx, code in fenced_blocks:
            all_blocks.append((idx, code, 'fenced'))
        for line_num, code, category in inline_blocks:
            all_blocks.append((line_num, code, category))

        total = len(all_blocks)
        if total == 0:
            return JacCheckResult(0, 0, 0, 0, 100.0, [])

        if max_workers is None:
            max_workers = min(32, (os.cpu_count() or 4) * 2)

        passed = 0
        failed = 0
        skipped = 0
        errors = []
        completed = 0
        progress_lock = Lock()

        def update_progress():
            nonlocal completed
            with progress_lock:
                completed += 1
                if on_progress:
                    on_progress(completed, total, f"Checked {completed}/{total} blocks")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._check_block_task, idx, code, source): (idx, code, source)
                for idx, code, source in all_blocks
            }

            for future in as_completed(futures):
                idx, code, source, success, error = future.result()
                update_progress()

                if success is None:
                    skipped += 1
                elif success:
                    passed += 1
                else:
                    failed += 1
                    preview = code[:200].replace('\n', ' ')
                    errors.append({
                        "line": idx,
                        "error": error,
                        "source": source,
                        "code": preview + "..." if len(code) > 200 else preview
                    })

        total_checked = passed + failed
        pass_rate = (passed / total_checked * 100) if total_checked > 0 else 100.0

        result = JacCheckResult(
            total_blocks=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=pass_rate,
            errors=errors
        )

        if errors and fail_on_error:
            error_summary = "\n".join(
                f"  [{e['source']}:{e['line']}] {e['error']}"
                for e in errors[:5]
            )
            raise ValidationError(
                f"{len(errors)} code blocks failed jac check:\n{error_summary}"
            )

        return result
