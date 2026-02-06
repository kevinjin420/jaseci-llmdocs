"""
Deterministic content extractor for Jac documentation.

Stage 1 of the lossless pipeline: extracts all content without LLM involvement.
Categorizes code blocks and signatures by construct type.
"""

import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CodeExample:
    code: str
    source_file: str
    construct_type: str
    has_keywords: list[str] = field(default_factory=list)
    line_count: int = 0

    def __post_init__(self):
        self.line_count = len(self.code.strip().split('\n'))


@dataclass
class ExtractedContent:
    signatures: dict[str, list[str]]  # construct_type -> list of signatures
    examples: dict[str, list[CodeExample]]  # construct_type -> list of examples
    keywords_found: set[str] = field(default_factory=set)
    total_examples: int = 0
    total_signatures: int = 0


class DeterministicExtractor:
    """Extracts content without LLM - purely deterministic."""

    CONSTRUCT_PATTERNS = {
        'node': r'\bnode\s+\w+',
        'edge': r'\bedge\s+\w+',
        'walker': r'\bwalker\s+\w+',
        'obj': r'\bobj\s+\w+',
        'enum': r'\benum\s+\w+',
        'glob': r'\bglob\s+\w+',
        'can': r'\bcan\s+\w+',
        'def': r'\bdef\s+\w+',
        'with_entry': r'with\s+.*?\s+entry',
        'with_exit': r'with\s+.*?\s+exit',
        'by_llm': r'by\s+llm\s*[;(]',
        'spawn': r'\bspawn\b',
        'visit': r'\bvisit\s+\[',
        'connect': r'\+\+>|<\+\+>|\+>:.*?:\+>|<\+:.*?:<\+',
        'traverse': r'\[.*?-->.*?\]|\[.*?<--.*?\]|\[.*?->:.*?:->.*?\]|\[.*?<-:.*?:<-.*?\]',
        'filter': r'\(\?\w+',
        'report': r'\breport\b',
        '__specs__': r'__specs__',
        'async': r'\basync\s+(walker|def)',
        'websocket': r'websocket',
        'serve': r'jac\s+serve',
        'client_block': r'\bcl\s*\{',
        'server_block': r'\bsv\s*\{',
        'jsx_element': r'<[A-Z]\w*[^>]*/>|<[A-Z]\w*[^>]*>',
        'jsx_fragment': r'<>|</>',
        'react_hook': r'\buse[A-Z]\w*\s*\(',
    }

    CRITICAL_KEYWORDS = [
        '++>', '<++>', '-->', '<-->', '+>:', ':<+', '->:', ':->',
        'spawn', 'visit', 'report', 'disengage',
        'here', 'self', 'visitor', 'props', 'by llm',
        'with entry', 'with exit', '`root', '.cl.jac', 'cl {', 'sv {',
        '</', '/>', 'useState', 'useEffect'
    ]

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.docs_validator = None
        root = Path(__file__).parents[2]
        template_path = root / "config" / "reference_template.yaml"
        if template_path.exists():
            with open(template_path) as f:
                self.template = yaml.safe_load(f)
        else:
            self.template = {'sections': [], 'keywords': {'critical': self.CRITICAL_KEYWORDS}}

        try:
            from .docs_validator import OfficialDocsValidator
            self.docs_validator = OfficialDocsValidator()
        except ImportError:
            pass

    def extract_from_directory(self, source_dir: Path) -> ExtractedContent:
        """Extract all content from sanitized markdown files."""
        content = ExtractedContent(
            signatures=defaultdict(list),
            examples=defaultdict(list),
            keywords_found=set()
        )

        # Extract from markdown files
        for md_file in source_dir.glob("*.md"):
            if 'skeleton' in md_file.name:
                self._extract_skeleton(md_file, content)
            else:
                self._extract_examples(md_file, content)

        content.total_examples = sum(len(v) for v in content.examples.values())
        content.total_signatures = sum(len(v) for v in content.signatures.values())

        return content

    def _extract_skeleton(self, file_path: Path, content: ExtractedContent):
        """Extract signatures from skeleton file."""
        text = file_path.read_text()

        # Parse skeleton format: grouped by ## headers
        current_type = None
        current_block = []

        for line in text.split('\n'):
            if line.startswith('## '):
                if current_type and current_block:
                    sig = '\n'.join(current_block).strip()
                    if sig:
                        content.signatures[current_type].append(sig)
                current_type = line[3:].strip().lower()
                if current_type.endswith('s'):
                    current_type = current_type[:-1]  # nodes -> node
                current_block = []
            elif line.startswith('#'):
                continue
            elif line.strip():
                current_block.append(line)
            elif current_block:
                # Empty line - save current block
                sig = '\n'.join(current_block).strip()
                if sig and current_type:
                    content.signatures[current_type].append(sig)
                current_block = []

        # Don't forget last block
        if current_type and current_block:
            sig = '\n'.join(current_block).strip()
            if sig:
                content.signatures[current_type].append(sig)

    def _extract_examples(self, file_path: Path, content: ExtractedContent):
        """Extract code examples from markdown file."""
        text = file_path.read_text()

        # Find all code blocks
        code_pattern = re.compile(r'```(jac|python)?\s*\n(.*?)```', re.DOTALL)

        for match in code_pattern.finditer(text):
            lang = match.group(1) or 'jac'
            code = match.group(2).strip()

            if not code or len(code) < 20:
                continue

            # Determine construct type(s) this example demonstrates
            construct_types = self._classify_code(code)
            keywords = self._find_keywords(code)

            content.keywords_found.update(keywords)

            example = CodeExample(
                code=code,
                source_file=file_path.name,
                construct_type=construct_types[0] if construct_types else 'general',
                has_keywords=keywords
            )

            # Add to primary construct type
            if construct_types:
                content.examples[construct_types[0]].append(example)
                # Also index by secondary types
                for ct in construct_types[1:]:
                    content.examples[ct].append(example)
            else:
                content.examples['general'].append(example)

    def _classify_code(self, code: str) -> list[str]:
        """Classify code block by construct types it demonstrates."""
        types = []
        for construct, pattern in self.CONSTRUCT_PATTERNS.items():
            if re.search(pattern, code, re.IGNORECASE):
                types.append(construct)
        return types

    def _find_keywords(self, code: str) -> list[str]:
        """Find critical keywords present in code."""
        found = []
        for kw in self.CRITICAL_KEYWORDS:
            if kw in code:
                found.append(kw)
        return found

    def select_best_examples(self, content: ExtractedContent, max_per_type: int = 3) -> dict[str, list[CodeExample]]:
        """Select best examples for each construct type."""
        selected = {}

        # Construct patterns that MUST appear for an example to be valid for that type
        construct_requirements = {
            'node': r'\bnode\s+\w+',
            'edge': r'\bedge\s+\w+',
            'walker': r'\bwalker\s+\w+',
            'obj': r'\bobj\s+\w+',
            'enum': r'\benum\s+\w+',
            'can': r'\bcan\s+\w+',
            'def': r'\bdef\s+\w+',
            'with_entry': r'with\s+.*?\s+entry',
            'with_exit': r'with\s+.*?\s+exit',
            'by_llm': r'by\s+llm',
            'spawn': r'\bspawn\b',
            'visit': r'\bvisit\b',
            'connect': r'\+\+>|<\+\+>',
            'traverse': r'-->|<--|->:.*?:->|<-:.*?:<-',
            'filter': r'\(\?\w+',
            'report': r'\breport\b',
        }

        for construct_type, examples in content.examples.items():
            if not examples:
                continue

            # Filter: example must contain the construct it claims to demonstrate
            requirement = construct_requirements.get(construct_type)
            if requirement:
                examples = [ex for ex in examples if re.search(requirement, ex.code)]

            if not examples:
                continue

            def score(ex: CodeExample) -> float:
                # Heavily penalize very long examples (likely reference files)
                if ex.line_count > 50:
                    return -100  # Reject outright
                if ex.line_count > 30:
                    length_score = -20
                elif 5 <= ex.line_count <= 20:
                    length_score = 30  # Sweet spot
                elif ex.line_count < 5:
                    length_score = ex.line_count * 3
                else:  # 20-30 lines
                    length_score = 20 - (ex.line_count - 20)

                # Moderate bonus for relevant keywords (cap it)
                keyword_score = min(len(ex.has_keywords) * 5, 25)

                # Bonus for focused examples (fewer constructs = more focused)
                construct_count = len(self._classify_code(ex.code))
                focus_score = max(0, 20 - construct_count * 3)

                # Bonus for complete patterns
                completeness = 0
                if 'spawn' in ex.code and 'walker' in ex.code:
                    completeness += 10
                if 'visit' in ex.code and ('++>' in ex.code or '-->' in ex.code):
                    completeness += 10
                if 'with entry' in ex.code.lower():
                    completeness += 5

                return length_score + keyword_score + focus_score + completeness

            sorted_examples = sorted(examples, key=score, reverse=True)

            # Deduplicate: use first 150 chars as signature
            seen_signatures = set()
            unique = []
            for ex in sorted_examples:
                if score(ex) < 0:
                    continue
                # Create a rough signature from normalized code
                sig = re.sub(r'\s+', ' ', ex.code[:150].lower())
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    unique.append(ex)
                    if len(unique) >= max_per_type:
                        break

            selected[construct_type] = unique

        return selected

    def format_for_assembly(self, content: ExtractedContent) -> str:
        """Format extracted content for LLM assembly stage."""
        best_examples = self.select_best_examples(content)

        output = []
        output.append("# EXTRACTED SIGNATURES")
        output.append("")

        for construct_type in ['node', 'edge', 'walker', 'obj', 'enum', 'function', 'glob']:
            if construct_type in content.signatures and content.signatures[construct_type]:
                output.append(f"## {construct_type.upper()}")
                # Deduplicate signatures
                seen = set()
                for sig in content.signatures[construct_type][:10]:  # Limit to 10
                    normalized = re.sub(r'\s+', ' ', sig.strip())
                    if normalized not in seen and len(normalized) > 10:
                        seen.add(normalized)
                        output.append(sig)
                        output.append("")

        output.append("")
        output.append("# EXTRACTED EXAMPLES")
        output.append("")

        for construct_type, examples in best_examples.items():
            if examples:
                output.append(f"## {construct_type.upper()} EXAMPLES")
                for ex in examples:
                    output.append(f"# From: {ex.source_file}")
                    output.append(f"# Keywords: {', '.join(ex.has_keywords)}")
                    output.append("```jac")
                    output.append(ex.code)
                    output.append("```")
                    output.append("")

        output.append("")
        output.append(f"# KEYWORDS FOUND: {', '.join(sorted(content.keywords_found))}")

        syntax_verification = self._verify_syntax_patterns()
        if syntax_verification:
            output.append("")
            output.append("# SYNTAX VERIFICATION (from official docs)")
            for name, verified in syntax_verification.items():
                status = "OK" if verified else "NOT FOUND"
                output.append(f"# - {name}: {status}")

        return '\n'.join(output)

    def _verify_syntax_patterns(self) -> dict[str, bool]:
        """Verify critical syntax patterns against official docs."""
        if not self.docs_validator:
            return {}

        patterns_to_verify = {
            'spawn': 'root spawn Walker()',
            'connect': '+>: EdgeType() :+>',
            'traverse': '[->:EdgeType:->]',
            'entry': 'with `root entry',
            'tuple_unpack': '(a, b) =',
            'by_llm': 'by llm;',
        }

        results = {}
        for name, pattern in patterns_to_verify.items():
            verification = self.docs_validator.verify_pattern(pattern)
            results[name] = verification.found_in_docs

        return results

    def get_canonical_examples(self) -> dict[str, str]:
        """Get canonical syntax examples from official docs for critical constructs."""
        if not self.docs_validator:
            return {}

        canonical = {}
        for construct, info in self.docs_validator.CANONICAL_PATTERNS.items():
            canonical[construct] = info['example']

        return canonical
