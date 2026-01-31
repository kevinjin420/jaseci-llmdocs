"""
Deterministic template-based assembler.
No LLM involvement - 100% reproducible output.
"""
import yaml
from pathlib import Path
from dataclasses import dataclass
from .deterministic_extractor import ExtractedContent, DeterministicExtractor


@dataclass
class Topic:
    id: str
    title: str
    prose: str
    constructs: list[str]
    max_examples: int
    full_examples: bool = False


class TemplateAssembler:
    """Assembles documentation using templates - no LLM."""

    def __init__(self, config_path: Path = None):
        self.root = Path(__file__).parents[2]
        topics_path = config_path or self.root / "config" / "topics.yaml"

        with open(topics_path) as f:
            data = yaml.safe_load(f)

        self.topics = [
            Topic(
                id=t['id'],
                title=t['title'],
                prose=t.get('prose'),
                constructs=t.get('constructs', []),
                max_examples=t.get('max_examples', 0),
                full_examples=t.get('full_examples', False)
            )
            for t in data['topics']
        ]
        self.extractor = DeterministicExtractor()

    def assemble(self, extracted: ExtractedContent) -> str:
        """Assemble final document from extracted content."""
        best_examples = self.extractor.select_best_examples(
            extracted, max_per_type=10
        )

        output = []
        used_code_signatures = set()

        def get_signature(code: str) -> str:
            """Create a signature to detect duplicate examples."""
            import re
            normalized = re.sub(r'\s+', ' ', code[:200].lower())
            return normalized

        def format_example(code: str, full: bool, max_lines: int = 15) -> str:
            """Format example, truncating at logical boundaries."""
            lines = code.strip().split('\n')

            if full or len(lines) <= max_lines:
                return code.strip()

            cut_point = None

            for i in range(max_lines, min(max_lines + 3, len(lines))):
                line = lines[i].rstrip()
                if line == '}' and (len(line) - len(line.lstrip()) == 0):
                    cut_point = i + 1
                    break

            if cut_point is None:
                for i in range(min(max_lines, len(lines)) - 1, 5, -1):
                    line = lines[i].rstrip()
                    indent = len(line) - len(line.lstrip())
                    if line == '}' and indent == 0:
                        cut_point = i + 1
                        break
                    if line.endswith('}') and indent == 0:
                        cut_point = i + 1
                        break
                    if not line and i > 8:
                        next_line = lines[i + 1].rstrip() if i + 1 < len(lines) else ''
                        next_indent = len(next_line) - len(next_line.lstrip()) if next_line else 0
                        if next_indent == 0 or not next_line:
                            cut_point = i
                            break

            if cut_point is None:
                cut_point = max_lines

            result = '\n'.join(lines[:cut_point])

            remaining = len(lines) - cut_point
            if remaining > 2:
                result += '\n    ...'

            return result

        for topic in self.topics:
            output.append(topic.title)

            if topic.prose:
                output.append(topic.prose)

            if topic.max_examples > 0:
                topic_examples = []
                for construct in topic.constructs:
                    for ex in best_examples.get(construct, []):
                        sig = get_signature(ex.code)
                        if sig not in used_code_signatures:
                            topic_examples.append(ex)
                            if len(topic_examples) >= topic.max_examples:
                                break
                    if len(topic_examples) >= topic.max_examples:
                        break

                for ex in topic_examples:
                    sig = get_signature(ex.code)
                    used_code_signatures.add(sig)
                    output.append(format_example(ex.code, topic.full_examples))

            output.append('')

        return '\n'.join(output)

    def assemble_from_directory(self, source_dir: Path) -> str:
        """Extract and assemble from source directory."""
        extracted = self.extractor.extract_from_directory(source_dir)
        return self.assemble(extracted)
