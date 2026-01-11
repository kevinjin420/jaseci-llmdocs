import re
from pathlib import Path
from .validator import Validator


class Compressor:
    def __init__(self, llm, config: dict):
        self.out_dir = Path(config.get('ultra_compression', {}).get('output_dir', 'output/4_final'))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.validator = Validator()

    def run(self, in_path: Path, out_name: str):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        print("Stage 4: Minifying (deterministic)...")

        text = in_path.read_text()
        minified = self.minify(text)

        result = self.validator.validate_final(minified)
        if not result.is_valid:
            print(f"  Warning: {result.issues}")
            if result.missing_patterns:
                print(f"  Missing: {result.missing_patterns[:5]}")

        out_path = self.out_dir / out_name
        out_path.write_text(minified)
        print(f"  Saved {len(text)} -> {len(minified)} chars ({len(minified)/len(text):.1%})")
        return {'success': True}

    def minify(self, text: str) -> str:
        code_blocks = []

        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f"__CODEBLOCK_{len(code_blocks) - 1}__"

        protected = re.sub(r'```[\s\S]*?```', save_code_block, text)

        protected = re.sub(r'[ \t]+', ' ', protected)
        protected = re.sub(r'\n{3,}', '\n\n', protected)

        lines = []
        in_list = False

        for line in protected.split('\n'):
            stripped = line.strip()

            if not stripped:
                if lines and lines[-1] != '':
                    lines.append('')
                continue

            if stripped.startswith('__CODEBLOCK_'):
                lines.append(stripped)
                in_list = False
                continue

            if stripped.startswith('#'):
                if lines and lines[-1] != '':
                    lines.append('')
                lines.append(stripped)
                in_list = False
                continue

            if stripped.startswith('-') or stripped.startswith('*') or re.match(r'^\d+\.', stripped):
                lines.append(stripped)
                in_list = True
                continue

            if in_list:
                lines.append(stripped)
                in_list = False
                continue

            if lines and lines[-1] and not lines[-1].startswith('#') and not lines[-1].startswith('__CODEBLOCK_'):
                if not lines[-1].startswith('-') and not lines[-1].startswith('*'):
                    lines[-1] += ' ' + stripped
                    continue

            lines.append(stripped)

        result = '\n'.join(lines)

        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')

        for i, block in enumerate(code_blocks):
            minified_block = self._minify_code_block(block)
            result = result.replace(f"__CODEBLOCK_{i}__", minified_block)

        return result.strip()

    def _minify_code_block(self, block: str) -> str:
        """Minify code block while preserving structure."""
        lines = block.split('\n')
        if len(lines) < 2:
            return block

        result = [lines[0]]

        for line in lines[1:-1]:
            stripped = line.rstrip()
            if stripped:
                result.append(stripped)

        if lines[-1].strip() == '```':
            result.append('```')
        else:
            result.append(lines[-1])

        return '\n'.join(result)
