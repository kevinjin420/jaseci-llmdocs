import re
import shutil
from pathlib import Path

from .sources import SourceManager, SourceType
from .semantic_extractor import SemanticExtractor
from .lark_extractor import LarkExtractor


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
        config_path = Path(__file__).parents[2] / "config" / "config.yaml"
        self.source_manager = SourceManager(config_path)
        self.semantic_extractor = SemanticExtractor(config)
        self.lark_extractor = LarkExtractor(config)

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

    def run(self, docs_dir: Path, out_dir: Path, on_fetch_progress=None) -> dict:
        """Fetch from all sources and process files."""
        fetch_dir = docs_dir.parent / "fetched"

        if on_fetch_progress:
            fetch_results = self.source_manager.fetch_all_parallel(
                fetch_dir, max_workers=4, on_progress=on_fetch_progress
            )
        else:
            fetch_results = self.source_manager.fetch_all(fetch_dir)

        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        stats = {
            "sources": fetch_results["sources"],
            "total_files": 0,
            "kept_files": 0,
            "excluded_files": 0,
            "empty_files": 0,
            "jac_files": 0,
            "jac_definitions": 0,
            "files": []
        }

        for source_stats in fetch_results["sources"]:
            source_id = source_stats["source_id"]
            source_dir = fetch_dir / source_id
            source = self.source_manager.get(source_id)

            if not source_dir.exists():
                continue

            if source.source_type in (SourceType.DOCS, SourceType.BOTH):
                md_files = list(source_dir.glob("*.md"))
                stats["total_files"] += len(md_files)

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
                    if dest_path.exists():
                        dest_path = out_dir / f"{source_id}_{src_path.name}"

                    dest_path.write_text(cleaned, encoding='utf-8')

                    stats["kept_files"] += 1
                    stats["files"].append({
                        "path": dest_path.name,
                        "source": source_id,
                        "type": "docs",
                        "original_size": len(raw),
                        "cleaned_size": len(cleaned)
                    })

            if source.source_type in (SourceType.JAC, SourceType.BOTH):
                ast_results = self.lark_extractor.process_directory(source_dir)
                stats["jac_files"] += ast_results["totals"]["files"]
                stats["jac_definitions"] += len(ast_results["all_definitions"])

                if ast_results["all_definitions"]:
                    skeleton = self.lark_extractor.generate_skeleton(ast_results)
                    skeleton_path = out_dir / f"{source_id}_jac_skeleton.md"
                    skeleton_path.write_text(skeleton, encoding='utf-8')

                    stats["kept_files"] += 1
                    stats["files"].append({
                        "path": skeleton_path.name,
                        "source": source_id,
                        "type": "jac",
                        "original_size": len(skeleton),
                        "cleaned_size": len(skeleton),
                        "definitions": len(ast_results["all_definitions"])
                    })

        self._extract_skeletons_from_markdown(out_dir, stats)

        return stats

    def _extract_skeletons_from_markdown(self, out_dir: Path, stats: dict):
        """Extract Jac skeletons from code blocks in markdown files."""
        all_definitions = []

        for file_info in stats["files"]:
            if file_info["type"] != "docs":
                continue

            file_path = out_dir / file_info["path"]
            try:
                content = file_path.read_text(encoding='utf-8')
                definitions = self.semantic_extractor.extract_from_markdown(content)
                all_definitions.extend(definitions)
            except Exception:
                continue

        if all_definitions:
            results = {
                "all_definitions": all_definitions,
                "totals": {"files": len([f for f in stats["files"] if f["type"] == "docs"])}
            }
            skeleton = self.semantic_extractor.generate_skeleton(results)
            skeleton_path = out_dir / "docs_jac_skeleton.md"
            skeleton_path.write_text(skeleton, encoding='utf-8')

            stats["kept_files"] += 1
            stats["files"].append({
                "path": skeleton_path.name,
                "source": "docs",
                "type": "skeleton",
                "original_size": 0,
                "cleaned_size": len(skeleton),
                "definitions": len(all_definitions)
            })
