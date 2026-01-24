"""Git operations with Python interop."""

import:py subprocess;
import:py tempfile;
import:py shutil;
import:py from pathlib import Path;

can fetch_source(
    git_url: str,
    branch: str,
    path: str,
    patterns: list[str],
    out_dir: str,
    source_id: str
) -> dict {
    """Fetch files from a Git repository using sparse checkout."""
    stats = {
        "source_id": source_id,
        "files": [],
        "total": 0,
        "errors": []
    };

    try {
        with tempfile.TemporaryDirectory() as tmp {
            tmp_dir = Path(tmp);

            subprocess.run(
                ["git", "init"],
                cwd=tmp_dir,
                capture_output=True,
                check=True
            );
            subprocess.run(
                ["git", "remote", "add", "origin", git_url],
                cwd=tmp_dir,
                capture_output=True,
                check=True
            );
            subprocess.run(
                ["git", "config", "core.sparseCheckout", "true"],
                cwd=tmp_dir,
                capture_output=True,
                check=True
            );

            sparse_file = tmp_dir / ".git" / "info" / "sparse-checkout";
            sparse_file.parent.mkdir(parents=True, exist_ok=True);
            sparse_file.write_text(f"{path}/*\n");

            result = subprocess.run(
                ["git", "pull", "--depth=1", "origin", branch],
                cwd=tmp_dir,
                capture_output=True,
                text=True
            );

            if result.returncode != 0 {
                stats["errors"].append(f"Git pull failed: {result.stderr}");
                return stats;
            }

            source_dir = tmp_dir / path;
            if not source_dir.exists() {
                source_dir = tmp_dir;
                for part in path.split('/') {
                    source_dir = source_dir / part;
                    if not source_dir.exists() {
                        break;
                    }
                }
            }

            if not source_dir.exists() {
                stats["errors"].append(f"Path '{path}' not found in repo");
                return stats;
            }

            out_path = Path(out_dir) / source_id;
            out_path.mkdir(parents=True, exist_ok=True);

            for pattern in patterns {
                for file_path in source_dir.rglob(pattern) {
                    if file_path.is_file() {
                        rel_path = file_path.relative_to(source_dir);
                        dest = out_path / rel_path.name;

                        if dest.exists() {
                            stem = file_path.stem;
                            parent = file_path.parent.name;
                            dest = out_path / f"{parent}_{stem}{file_path.suffix}";
                        }

                        shutil.copy2(file_path, dest);
                        stats["files"].append({
                            "name": dest.name,
                            "size": dest.stat().st_size,
                            "type": file_path.suffix
                        });
                        stats["total"] += 1;
                    }
                }
            }
        }
    } except subprocess.CalledProcessError as e {
        stats["errors"].append(f"Git command failed: {e}");
    } except Exception as e {
        stats["errors"].append(str(e));
    }

    return stats;
}

can fetch_all_sources(sources: list, out_dir: str) -> dict {
    """Fetch all enabled sources."""
    import:py from pathlib import Path;

    out_path = Path(out_dir);
    if out_path.exists() {
        shutil.rmtree(out_path);
    }
    out_path.mkdir(parents=True);

    results = {
        "sources": [],
        "total_files": 0,
        "total_errors": 0
    };

    for source in sources {
        patterns = source.file_patterns.split(',') if source.file_patterns else ["*.md"];
        patterns = [p.strip() for p in patterns];

        stats = fetch_source(
            git_url=source.git_url,
            branch=source.branch,
            path=source.path,
            patterns=patterns,
            out_dir=out_dir,
            source_id=source.id
        );

        results["sources"].append(stats);
        results["total_files"] += stats["total"];
        results["total_errors"] += len(stats["errors"]);
    }

    return results;
}
