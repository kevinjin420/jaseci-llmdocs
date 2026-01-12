import re
import shutil
import subprocess
import tempfile
from pathlib import Path

JASECI_REPO = "https://github.com/jaseci-labs/jaseci.git"
DOCS_PATH = "docs/docs"

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

    def fetch_docs(self, out_dir: Path) -> dict:
        """Fetch latest docs from Jaseci repo, extract only .md files flattened."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            subprocess.run(["git", "init"], cwd=tmp_dir, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", JASECI_REPO], cwd=tmp_dir, capture_output=True)
            subprocess.run(["git", "config", "core.sparseCheckout", "true"], cwd=tmp_dir, capture_output=True)

            sparse_file = tmp_dir / ".git" / "info" / "sparse-checkout"
            sparse_file.parent.mkdir(parents=True, exist_ok=True)
            sparse_file.write_text(f"{DOCS_PATH}/*\n")

            result = subprocess.run(
                ["git", "pull", "--depth=1", "origin", "main"],
                cwd=tmp_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise Exception(f"Failed to fetch docs: {result.stderr}")

            if out_dir.exists():
                shutil.rmtree(out_dir)
            out_dir.mkdir(parents=True)

            source_dir = tmp_dir / "docs" / "docs"
            md_files = list(source_dir.rglob("*.md"))

            copied = 0
            seen_names = set()
            for md_file in md_files:
                name = md_file.name

                if name.lower() in ("index.md", "readme.md"):
                    continue

                if name in seen_names:
                    stem = md_file.stem
                    parent = md_file.parent.name
                    name = f"{parent}_{stem}.md"

                seen_names.add(name)
                shutil.copy2(md_file, out_dir / name)
                copied += 1

            return {"fetched_files": copied}

    def should_exclude(self, path: Path) -> bool:
        parts = set(path.parts)
        if parts & EXCLUDE_DIRS:
            return True
        for pattern in EXCLUDE_PATTERNS:
            if path.match(pattern):
                return True
        return False

    def clean_markdown(self, text: str) -> str:
        text = re.sub(r'^---\n.*?\n---\n?', '', text, flags=re.DOTALL)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        text = re.sub(r'^(Next|Previous|Back|Continue):\s*\[.*?\]\(.*?\)\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'!\[.*?\]\(https?://.*?badge.*?\)', '', text)
        text = re.sub(r'!\[.*?\]\(https?://img\.shields\.io.*?\)', '', text)

        lines = text.split('\n')
        cleaned = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if re.match(r'^#{1,6}\s+', line):
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and re.match(r'^#{1,6}\s+', lines[j]):
                    i += 1
                    continue
            cleaned.append(line)
            i += 1

        text = '\n'.join(cleaned)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def has_useful_content(self, text: str) -> bool:
        if len(text) < self.min_content_length:
            return False

        if re.search(r'```(jac|python|py|javascript|js|bash|sh)?', text):
            return True

        jac_patterns = [
            r'\+\+>',
            r'-->',
            r'by\s+llm',
            r'with\s+entry',
            r'\bspawn\b',
            r'\bwalker\b',
            r'\bnode\b',
            r'\bedge\b',
            r'\bcan\b\s+\w+',
            r'::\w+:',
        ]
        for p in jac_patterns:
            if re.search(p, text, re.IGNORECASE):
                return True

        return len(text) > 500

    def run(self, docs_dir: Path, out_dir: Path) -> dict:
        # Fetch latest docs
        fetch_stats = self.fetch_docs(docs_dir)

        # Clean output dir
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        stats = {
            "fetched_files": fetch_stats["fetched_files"],
            "total_files": 0,
            "kept_files": 0,
            "excluded_files": 0,
            "empty_files": 0,
            "files": []
        }

        md_files = list(docs_dir.glob("*.md"))
        stats["total_files"] = len(md_files)

        for src_path in md_files:
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

            dest_path = out_dir / src_path.name
            dest_path.write_text(cleaned, encoding='utf-8')

            stats["kept_files"] += 1
            stats["files"].append({
                "path": src_path.name,
                "original_size": len(raw),
                "cleaned_size": len(cleaned)
            })

        return stats
