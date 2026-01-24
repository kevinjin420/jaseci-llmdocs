"""Deterministic content extractor for Jac documentation."""

include:jac utils.patterns;

import:py re;
import:py from pathlib import Path;
import:py from collections import defaultdict;

obj CodeExample {
    has code: str;
    has source_file: str;
    has construct_type: str;
    has has_keywords: list[str] = [];
    has line_count: int = 0;

    can :postinit: {
        self.line_count = len(self.code.strip().split("\n"));
    }
}

obj ExtractedContent {
    has signatures: dict = {};
    has examples: dict = {};
    has keywords_found: set = set();
    has total_examples: int = 0;
    has total_signatures: int = 0;
}

obj DeterministicExtractor {
    has config: dict = {};

    can extract_from_directory(
        source_dir: str | object,
        progress_callback: object | None = None
    ) -> ExtractedContent {
        """Extract all content from sanitized markdown files."""
        if isinstance(source_dir, str) {
            source_dir = Path(source_dir);
        }

        content = ExtractedContent(
            signatures=defaultdict(list),
            examples=defaultdict(list),
            keywords_found=set()
        );

        md_files = list(source_dir.glob("*.md"));
        total = len(md_files);

        for (i, md_file) in enumerate(md_files) {
            if progress_callback is not None {
                progress_callback(i + 1, total, f"Extracting from {md_file.name}");
            }

            if "skeleton" in md_file.name {
                self._extract_skeleton(md_file, content);
            } else {
                self._extract_examples(md_file, content);
            }
        }

        content.total_examples = sum(len(v) for v in content.examples.values());
        content.total_signatures = sum(len(v) for v in content.signatures.values());

        return content;
    }

    can _extract_skeleton(file_path: object, content: ExtractedContent) {
        """Extract signatures from skeleton file."""
        text = file_path.read_text();

        current_type: str | None = None;
        current_block: list[str] = [];

        for line in text.split("\n") {
            if line.startswith("## ") {
                if current_type is not None and current_block {
                    sig = "\n".join(current_block).strip();
                    if sig {
                        content.signatures[current_type].append(sig);
                    }
                }
                current_type = line[3:].strip().lower();
                if current_type.endswith("s") {
                    current_type = current_type[:-1];
                }
                current_block = [];
            } elif line.startswith("#") {
                continue;
            } elif line.strip() {
                current_block.append(line);
            } elif current_block {
                sig = "\n".join(current_block).strip();
                if sig and current_type is not None {
                    content.signatures[current_type].append(sig);
                }
                current_block = [];
            }
        }

        if current_type is not None and current_block {
            sig = "\n".join(current_block).strip();
            if sig {
                content.signatures[current_type].append(sig);
            }
        }
    }

    can _extract_examples(file_path: object, content: ExtractedContent) {
        """Extract code examples from markdown file."""
        text = file_path.read_text();

        code_pattern = re.compile(r"```(jac|python)?\s*\n(.*?)```", re.DOTALL);

        for match in code_pattern.finditer(text) {
            code = match.group(2).strip();

            if not code or len(code) < 20 {
                continue;
            }

            construct_types = classify_code(code);
            keywords = find_keywords(code);

            content.keywords_found.update(keywords);

            example = CodeExample(
                code=code,
                source_file=file_path.name,
                construct_type=construct_types[0] if construct_types else "general",
                has_keywords=keywords
            );

            if construct_types {
                content.examples[construct_types[0]].append(example);
                for ct in construct_types[1:] {
                    content.examples[ct].append(example);
                }
            } else {
                content.examples["general"].append(example);
            }
        }
    }

    can select_best_examples(
        content: ExtractedContent,
        max_per_type: int = 3
    ) -> dict[str, list[CodeExample]] {
        """Select best examples for each construct type."""
        selected: dict = {};

        construct_requirements = {
            "node": r"\bnode\s+\w+",
            "edge": r"\bedge\s+\w+",
            "walker": r"\bwalker\s+\w+",
            "obj": r"\bobj\s+\w+",
            "enum": r"\benum\s+\w+",
            "can": r"\bcan\s+\w+",
            "def": r"\bdef\s+\w+",
            "with_entry": r"with\s+.*?\s+entry",
            "with_exit": r"with\s+.*?\s+exit",
            "by_llm": r"by\s+llm",
            "spawn": r"\bspawn\b",
            "visit": r"\bvisit\b",
            "connect": r"\+\+>|<\+\+>",
            "traverse": r"-->|<--",
            "filter": r"\(\?\w+",
            "report": r"\breport\b"
        };

        for (construct_type, examples) in content.examples.items() {
            if not examples {
                continue;
            }

            requirement = construct_requirements.get(construct_type);
            if requirement {
                examples = [ex for ex in examples if re.search(requirement, ex.code)];
            }

            if not examples {
                continue;
            }

            can score(ex: CodeExample) -> float {
                if ex.line_count > 50 {
                    return -100;
                }
                if ex.line_count > 30 {
                    length_score = -20;
                } elif 5 <= ex.line_count <= 20 {
                    length_score = 30;
                } elif ex.line_count < 5 {
                    length_score = ex.line_count * 3;
                } else {
                    length_score = 20 - (ex.line_count - 20);
                }

                keyword_score = min(len(ex.has_keywords) * 5, 25);

                construct_count = len(classify_code(ex.code));
                focus_score = max(0, 20 - construct_count * 3);

                completeness = 0;
                if "spawn" in ex.code and "walker" in ex.code {
                    completeness += 10;
                }
                if "visit" in ex.code and ("++" in ex.code or "-->" in ex.code) {
                    completeness += 10;
                }
                if "with entry" in ex.code.lower() {
                    completeness += 5;
                }

                return length_score + keyword_score + focus_score + completeness;
            }

            sorted_examples = sorted(examples, key=score, reverse=True);

            seen_signatures: set = set();
            unique: list = [];
            for ex in sorted_examples {
                if score(ex) < 0 {
                    continue;
                }
                sig = re.sub(r"\s+", " ", ex.code[:150].lower());
                if sig not in seen_signatures {
                    seen_signatures.add(sig);
                    unique.append(ex);
                    if len(unique) >= max_per_type {
                        break;
                    }
                }
            }

            selected[construct_type] = unique;
        }

        return selected;
    }

    can format_for_assembly(content: ExtractedContent) -> str {
        """Format extracted content for LLM assembly stage."""
        best_examples = self.select_best_examples(content);

        output: list[str] = [];
        output.append("# EXTRACTED SIGNATURES");
        output.append("");

        for construct_type in ["node", "edge", "walker", "obj", "enum", "function", "glob"] {
            if construct_type in content.signatures and content.signatures[construct_type] {
                output.append(f"## {construct_type.upper()}");
                seen: set = set();
                for sig in content.signatures[construct_type][:10] {
                    normalized = re.sub(r"\s+", " ", sig.strip());
                    if normalized not in seen and len(normalized) > 10 {
                        seen.add(normalized);
                        output.append(sig);
                        output.append("");
                    }
                }
            }
        }

        output.append("");
        output.append("# EXTRACTED EXAMPLES");
        output.append("");

        for (construct_type, examples) in best_examples.items() {
            if examples {
                output.append(f"## {construct_type.upper()} EXAMPLES");
                for ex in examples {
                    output.append(f"# From: {ex.source_file}");
                    output.append(f"# Keywords: {', '.join(ex.has_keywords)}");
                    output.append("```jac");
                    output.append(ex.code);
                    output.append("```");
                    output.append("");
                }
            }
        }

        output.append("");
        output.append(f"# KEYWORDS FOUND: {', '.join(sorted(content.keywords_found))}");

        return "\n".join(output);
    }
}
