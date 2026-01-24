"""Fetch and sanitize documentation sources."""

include:jac models.source;
include:jac utils.git;
include:jac utils.patterns;

import:py re;
import:py shutil;
import:py from pathlib import Path;

obj Sanitizer {
    has min_content_length: int = 200;

    can clean_markdown(text: str) -> str {
        """Clean and normalize markdown content."""
        text = re.sub(r"^---\n.*?\n---\n?", "", text, flags=re.DOTALL);
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL);
        text = re.sub(r"^(Next|Previous|Back|Continue):\s*\[.*?\]\(.*?\)\s*$", "", text, flags=re.MULTILINE);
        text = re.sub(r"!\[.*?\]\(https?://.*?badge.*?\)", "", text);
        text = re.sub(r"!\[.*?\]\(https?://img\.shields\.io.*?\)", "", text);

        lines = text.split("\n");
        cleaned: list[str] = [];
        i = 0;
        while i < len(lines) {
            line = lines[i];
            if re.match(r"^#{1,6}\s+", line) {
                j = i + 1;
                while j < len(lines) and not lines[j].strip() {
                    j += 1;
                }
                if j < len(lines) and re.match(r"^#{1,6}\s+", lines[j]) {
                    i += 1;
                    continue;
                }
            }
            cleaned.append(line);
            i += 1;
        }

        text = "\n".join(cleaned);
        text = re.sub(r"\n{3,}", "\n\n", text);
        return text.strip();
    }

    can has_useful_content(text: str) -> bool {
        """Check if text contains useful documentation content."""
        if len(text) < self.min_content_length {
            return False;
        }

        if re.search(r"```(jac|python|py|javascript|js|bash|sh)?", text) {
            return True;
        }

        jac_patterns = [
            r"\+\+>",
            r"-->",
            r"by\s+llm",
            r"with\s+entry",
            r"\bspawn\b",
            r"\bwalker\b",
            r"\bnode\b",
            r"\bedge\b",
            r"\bcan\b\s+\w+",
            r"::\w+:"
        ];

        for p in jac_patterns {
            if re.search(p, text, re.IGNORECASE) {
                return True;
            }
        }

        return len(text) > 500;
    }

    can :async: fetch_and_sanitize(
        sources: list,
        progress_callback: object | None = None
    ) -> dict {
        """Fetch from sources and sanitize content."""
        fetch_dir = Path("output/0_fetched");
        out_dir = Path("output/1_sanitized");

        fetch_results = fetch_all_sources(sources, str(fetch_dir));

        if out_dir.exists() {
            shutil.rmtree(out_dir);
        }
        out_dir.mkdir(parents=True);

        stats = {
            "sources": fetch_results["sources"],
            "total_files": 0,
            "kept_files": 0,
            "excluded_files": 0,
            "empty_files": 0,
            "files": [],
            "input_size": 0,
            "output_size": 0,
            "file_count": 0,
            "output_dir": str(out_dir)
        };

        total_files = fetch_results["total_files"];
        processed = 0;

        for source_stats in fetch_results["sources"] {
            source_id = source_stats["source_id"];
            source_dir = fetch_dir / source_id;

            if not source_dir.exists() {
                continue;
            }

            md_files = list(source_dir.glob("*.md"));
            stats["total_files"] += len(md_files);

            for src_path in md_files {
                processed += 1;
                if progress_callback is not None {
                    await progress_callback(processed, total_files, f"Processing {src_path.name}");
                }

                if should_exclude(src_path) {
                    stats["excluded_files"] += 1;
                    continue;
                }

                try {
                    raw = src_path.read_text(encoding="utf-8");
                    stats["input_size"] += len(raw);
                } except Exception {
                    continue;
                }

                cleaned = self.clean_markdown(raw);

                if not self.has_useful_content(cleaned) {
                    stats["empty_files"] += 1;
                    continue;
                }

                dest_path = out_dir / src_path.name;
                if dest_path.exists() {
                    dest_path = out_dir / f"{source_id}_{src_path.name}";
                }

                dest_path.write_text(cleaned, encoding="utf-8");

                stats["kept_files"] += 1;
                stats["output_size"] += len(cleaned);
                stats["files"].append({
                    "path": dest_path.name,
                    "source": source_id,
                    "type": "docs",
                    "original_size": len(raw),
                    "cleaned_size": len(cleaned)
                });
            }
        }

        stats["file_count"] = stats["kept_files"];
        return stats;
    }
}
