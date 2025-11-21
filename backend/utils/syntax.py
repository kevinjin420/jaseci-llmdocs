"""Jac language syntax validation utilities"""

import re
from typing import List, Tuple


def patch_missing_braces(code: str) -> Tuple[str, bool]:
    """
    Patch missing closing braces/brackets/parentheses at the end of code.
    LLMs often truncate the final closing brace.
    Returns: (patched_code, was_patched)
    """
    was_patched = False
    original_code = code

    open_braces = code.count('{')
    close_braces = code.count('}')
    open_brackets = code.count('[')
    close_brackets = code.count(']')
    open_parens = code.count('(')
    close_parens = code.count(')')

    if open_braces > close_braces:
        missing = open_braces - close_braces
        code = code + '\n' + '}' * missing
        was_patched = True

    if open_brackets > close_brackets:
        missing = open_brackets - close_brackets
        code = code + ']' * missing
        was_patched = True

    if open_parens > close_parens:
        missing = open_parens - close_parens
        code = code + ')' * missing
        was_patched = True

    return code, was_patched


class SyntaxChecker:
    """Validates Jac language syntax"""

    @staticmethod
    def validate_element_strict(code: str, element: str) -> bool:
        """
        Strictly validate element presence with context-aware pattern matching.
        Returns True only if element appears in proper syntactic context.
        """
        code_normalized = ' '.join(code.split())

        strict_patterns = {
            'walker': r'\bwalker\s+\w+\s*\{',
            'node': r'\bnode\s+\w+\s*\{',
            'edge': r'\bedge\s+\w+\s*\{',
            'obj': r'\bobj\s+\w+\s*\{',
            'enum': r'\benum\s+\w+\s*\{',
            'has': r'\bhas\s+\w+\s*:\s*\w+',
            'can': r'\bcan\s+\w+\s+with\s+',
            'with entry': r'\bwith\s+entry\s*\{',
            'with exit': r'\bwith\s+exit\s*\{',
            'visit': r'\bvisit\s+[^\s;]+',
            'spawn': r'\bspawn\s+\w+\s*\(',
            'by llm': r'\bby\s+llm\s*\(',
            'import': r'\bimport\s+',
            'from': r'\bfrom\s+\w+\s*\{',
            'return': r'\breturn\s+',
            'report': r'\breport\s+',
            'def': r'\bdef\s+\w+\s*\(',
            'async': r'\basync\s+(walker|def)',
            '__specs__': r'\bobj\s+__specs__\s*\{',
            'socket.notify': r'socket\.notify(_channels)?\s*\(',
            'here': r'\bhere\s*\.',
            'self': r'\bself\s*\.',
            '-[': r'-\[\w+\]->',
            '-->': r'-->',
            '<--': r'<--',
        }

        if element in strict_patterns:
            pattern = strict_patterns[element]
            if re.search(pattern, code):
                return True
            return False

        if ':' in element and 'has' not in code:
            return False

        if element.startswith('def ') and 'def' in code:
            func_name = element.split()[1] if len(element.split()) > 1 else None
            if func_name:
                pattern = rf'\bdef\s+{re.escape(func_name)}\s*\([^)]*\)'
                return bool(re.search(pattern, code))

        for keyword in ['walker', 'node', 'edge', 'obj', 'enum']:
            if element.startswith(keyword + ' '):
                name = element.split()[1] if len(element.split()) > 1 else None
                if name:
                    pattern = rf'\b{keyword}\s+{re.escape(name)}\s*\{{'
                    return bool(re.search(pattern, code))

        if '.' in element and '(' not in element:
            method_pattern = re.escape(element) + r'\s*\('
            if re.search(method_pattern, code):
                return True
            return False

        if element.count('.') == 1 and '(' not in element:
            parts = element.split('.')
            if len(parts) == 2:
                pattern = rf'\b{re.escape(parts[0])}\.{re.escape(parts[1])}\b'
                return bool(re.search(pattern, code))

        if element.startswith('"') or element.startswith("'"):
            return element in code

        if element in ['==', '!=', '<=', '>=', '+=', '-=', '*=', '/=', '**', '//',
                       '<<', '>>', '&', '|', '^', '~', 'and', 'or', 'not', 'in', 'is']:
            return element in code

        if element.replace('_', '').isalnum():
            pattern = rf'\b{re.escape(element)}\b'
            return bool(re.search(pattern, code))
        else:
            return element in code

    @staticmethod
    def check_syntax(code: str) -> List[str]:
        """Enhanced syntax validation checks for Jac code"""
        checks = []

        if re.search(r'\bwith entry\b', code) and not re.search(r'with entry\s*{', code):
            checks.append("[WARN] 'with entry' should be followed by a block { }")

        if re.search(r'\bwith exit\b', code) and not re.search(r'with exit\s*{', code):
            checks.append("[WARN] 'with exit' should be followed by a block { }")

        for keyword in ['walker', 'node', 'edge', 'obj', 'enum']:
            if re.search(rf'\b{keyword}\s+\w+\b', code):
                if not re.search(rf'\b{keyword}\s+\w+\s*{{', code):
                    checks.append(f"[WARN] '{keyword}' declaration should be followed by opening brace {{")

        if re.search(r'\bcan\s+\w+\b', code):
            if not re.search(r'\bcan\s+\w+\s+with\s+', code):
                checks.append("[WARN] 'can' ability should include 'with' clause (e.g., 'can ability_name with entry')")

        if re.search(r'\bvisit\b(?!\s+[^\s;]+)', code):
            checks.append("[WARN] 'visit' should be followed by a target")

        if re.search(r'\bspawn\b', code) and not re.search(r'\bspawn\s+\w+\s*\(', code):
            checks.append("[WARN] 'spawn' should be followed by walker name and parentheses")

        if re.search(r'\bby\s+llm\b', code) and not re.search(r'\bby\s+llm\s*\(', code):
            checks.append("[WARN] 'by llm' should be followed by parentheses (e.g., 'by llm()')")

        if re.search(r'\bhas\s+\w+\s*[=;]', code):
            if not re.search(r'\bhas\s+\w+\s*:\s*\w+', code):
                checks.append("[WARN] 'has' attributes should have type annotations (e.g., 'has name: str')")

        if re.search(r'\basync\b', code):
            if not re.search(r'\basync\s+(walker|def)\b', code):
                checks.append("[WARN] 'async' should be used before 'walker' or 'def'")

        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            checks.append(f"[WARN] Mismatched braces: {open_braces} opening, {close_braces} closing")

        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            checks.append(f"[WARN] Mismatched brackets: {open_brackets} opening, {close_brackets} closing")

        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            checks.append(f"[WARN] Mismatched parentheses: {open_parens} opening, {close_parens} closing")

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('*#'):
                continue

            needs_semi = any(keyword in stripped for keyword in [
                'glob ', 'has ', 'print(', 'report ', 'import ', 'include ',
                'disengage', 'raise ', 'return ', 'break', 'continue'
            ])

            no_semi_start = ('def ', 'obj ', 'node ', 'edge ', 'walker ', 'enum ',
                            'can ', 'if ', 'elif ', 'else', 'for ', 'while ',
                            'try', 'except', 'match ', 'case ', 'async def',
                            'with ', 'class ')
            no_semi_end = ('{', '}', ':', ',', '\\')

            has_assignment = '=' in stripped and not stripped.startswith(no_semi_start)

            if (needs_semi or has_assignment) and not stripped.startswith(no_semi_start):
                if not stripped.endswith(no_semi_end) and not stripped.endswith(';'):
                    checks.append(f"[WARN] Line {i} may be missing semicolon: {stripped[:60]}")

        if re.search(r'has\s+\w+\s*=', code) and not re.search(r'has\s+\w+\s*:\s*\w+', code):
            checks.append("[WARN] Attributes should have type annotations (has name: type)")

        if re.search(r'def\s+\w+\s*\([^)]*\w+\s*\)', code):
            if not re.search(r'def\s+\w+\s*\([^)]*:\s*\w+', code):
                checks.append("[WARN] Function parameters should have type annotations")

        if 'def ' in code and 'return' in code:
            if not re.search(r'def\s+\w+[^{]*->\s*\w+', code):
                checks.append("[WARN] Functions with return statements should have return type annotations (-> type)")

        if re.search(r'\bnode\s+\w+\s+\w+', code):
            checks.append("[WARN] Node declaration should use 'node ClassName {' syntax")

        if re.search(r'\bedge\s+\w+\s+\w+', code):
            checks.append("[WARN] Edge declaration should use 'edge ClassName {' syntax")

        if re.search(r'\bwalker\s+\w+\s+\w+', code):
            checks.append("[WARN] Walker declaration should use 'walker ClassName {' syntax")

        if '-->' in code and not any(op in code for op in ['[-->', '-->]', '++>', '+>:']):
            checks.append("[WARN] Navigation operator '-->' should be used in visit statements with brackets")

        if 'visit' in code and not re.search(r'visit\s+\[', code):
            checks.append("[WARN] Visit statements should use bracket notation: visit [...]")

        if 'glob ' in code and ':g:' not in code:
            checks.append("[WARN] Global variables should be accessed with :g: notation")

        if '?' in code and '`?' not in code and 'visit' in code:
            checks.append("[WARN] Type filtering in visit should use backtick: `?Type")

        if 'spawn' in code and not re.search(r'(root|here|\w+)\s+spawn\s+\w+', code):
            checks.append("[WARN] Spawn should follow pattern: 'node spawn walker_instance'")

        if 'can ' in code and 'with' in code:
            if not re.search(r'can\s+\w+\s+with\s+(entry|exit)', code):
                checks.append("[WARN] Abilities should use 'can ability_name with entry/exit' syntax")

        if 'by llm(' in code and 'def' in code:
            if not re.search(r'def\s+\w+[^{]*by\s+llm\(\)', code):
                checks.append("[WARN] AI functions should use 'def func() -> type by llm()' syntax")

        if '__specs__' in code:
            if not re.search(r'obj\s+__specs__\s*{', code):
                checks.append("[WARN] Walker specs should use 'obj __specs__ { static has ... }' syntax")

        if re.search(r'import\s+\w+\s*(?!;|from)', code):
            checks.append("[WARN] Import statements should end with semicolon")

        if any(op in code for op in ['++>', '<++>', '+>:', '<+:']):
            if not re.search(r'\w+\s*(-->|<-->|<--|\+\+>|<\+\+>|\+>:|<\+:)', code):
                checks.append("[WARN] Connection operators should be used between nodes")

        return checks
