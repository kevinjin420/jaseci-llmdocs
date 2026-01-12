import re
import shutil
from pathlib import Path

EXCLUDE_PATTERNS = [
    "**/release_notes/**",
    "**/breaking_changes.md",
    "**/CHANGELOG.md",
    "**/CONTRIBUTING.md",
    "**/contributing/**",
    "**/internals/**",
    "**/playground/**",
    "**/roadmap.md",
    "**/index.md",
    "**/README.md",
]

EXCLUDE_DIRS = {"internals", "playground", "communityhub", "contributing"}


class Sanitizer:
    def __init__(self, config: dict):
        self.cfg = config
        self.min_content_length = 200

    def should_exclude(self, path: Path) -> bool:
        parts = set(path.parts)
        if parts & EXCLUDE_DIRS:
            return True
        for pattern in EXCLUDE_PATTERNS:
            if path.match(pattern):
                return True
        return False

    def clean_markdown(self, text: str) -> str:
        # Remove YAML frontmatter
        text = re.sub(r'^---\n.*?\n---\n?', '', text, flags=re.DOTALL)

        # Remove HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

        # Remove navigation links like "Next: ..." or "Previous: ..."
        text = re.sub(r'^(Next|Previous|Back|Continue):\s*\[.*?\]\(.*?\)\s*$', '', text, flags=re.MULTILINE)

        # Remove badge images
        text = re.sub(r'!\[.*?\]\(https?://.*?badge.*?\)', '', text)
        text = re.sub(r'!\[.*?\]\(https?://img\.shields\.io.*?\)', '', text)

        # Remove empty headers (headers with no content before next header)
        lines = text.split('\n')
        cleaned = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if re.match(r'^#{1,6}\s+', line):
                # Check if next non-empty line is also a header
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and re.match(r'^#{1,6}\s+', lines[j]):
                    i += 1
                    continue
            cleaned.append(line)
            i += 1

        text = '\n'.join(cleaned)

        # Remove excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def has_useful_content(self, text: str) -> bool:
        if len(text) < self.min_content_length:
            return False

        # Check for code blocks (jac, python, etc.)
        if re.search(r'```(jac|python|py|javascript|js|bash|sh)?', text):
            return True

        # Check for Jac-specific patterns
        jac_patterns = [
            r'\+\+>',          # edge operator
            r'-->',            # another edge
            r'by\s+llm',       # by llm
            r'with\s+entry',   # with entry
            r'\bspawn\b',      # spawn
            r'\bwalker\b',     # walker
            r'\bnode\b',       # node
            r'\bedge\b',       # edge
            r'\bcan\b\s+\w+',  # ability definition
            r'::\w+:',         # type annotation
        ]
        for p in jac_patterns:
            if re.search(p, text, re.IGNORECASE):
                return True

        # If text is long enough, it's probably useful
        return len(text) > 500

    def run(self, src_dir: Path, out_dir: Path) -> dict:
        out_dir.mkdir(parents=True, exist_ok=True)

        # Clean output dir
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        stats = {
            "total_files": 0,
            "kept_files": 0,
            "excluded_files": 0,
            "empty_files": 0,
            "files": []
        }

        md_files = list(src_dir.glob("**/*.md"))
        stats["total_files"] = len(md_files)

        for src_path in md_files:
            rel_path = src_path.relative_to(src_dir)

            if self.should_exclude(src_path):
                stats["excluded_files"] += 1
                continue

            try:
                raw = src_path.read_text(encoding='utf-8')
            except Exception:
                continue

            cleaned = self.clean_markdown(raw)

            if not self.has_useful_content(cleaned):
                stats["empty_files"] += 1
                continue

            dest_path = out_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_text(cleaned, encoding='utf-8')

            stats["kept_files"] += 1
            stats["files"].append({
                "path": str(rel_path),
                "original_size": len(raw),
                "cleaned_size": len(cleaned)
            })

        return stats
