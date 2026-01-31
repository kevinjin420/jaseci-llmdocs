from __future__ import annotations
import sqlite3
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum


class SourceType(str, Enum):
    DOCS = "docs"
    JAC = "jac"
    BOTH = "both"


@dataclass
class Source:
    id: str
    git_url: str
    branch: str
    path: str
    source_type: SourceType
    enabled: bool = True
    file_patterns: str = None

    def __post_init__(self):
        if self.file_patterns is None:
            if self.source_type == SourceType.DOCS:
                self.file_patterns = "*.md"
            elif self.source_type == SourceType.JAC:
                self.file_patterns = "*.jac"
            else:
                self.file_patterns = "*.md,*.jac"

    def get_patterns_list(self) -> list[str]:
        return [p.strip() for p in self.file_patterns.split(',')]

    def to_dict(self):
        return {
            'id': self.id,
            'git_url': self.git_url,
            'branch': self.branch,
            'path': self.path,
            'source_type': self.source_type.value,
            'enabled': self.enabled,
            'file_patterns': self.get_patterns_list(),
        }

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row[0],
            git_url=row[1],
            branch=row[2],
            path=row[3],
            source_type=SourceType(row[4]),
            enabled=bool(row[5]),
            file_patterns=row[6]
        )


class SourceManager:
    """Manages multiple Git sources for documentation and Jac files using SQLite."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.db_path = config_path.parent / "sources.db"
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'")
            if cursor.fetchone():
                col_cursor = conn.execute("PRAGMA table_info(sources)")
                columns = [row[1] for row in col_cursor.fetchall()]
                if 'name' in columns:
                    conn.execute('DROP TABLE sources')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    git_url TEXT NOT NULL,
                    branch TEXT DEFAULT 'main',
                    path TEXT DEFAULT '.',
                    source_type TEXT DEFAULT 'docs',
                    enabled INTEGER DEFAULT 1,
                    file_patterns TEXT
                )
            ''')
            conn.commit()

            cursor = conn.execute('SELECT COUNT(*) FROM sources')
            if cursor.fetchone()[0] == 0:
                self._add_default(conn)

    def _add_default(self, conn):
        conn.execute('''
            INSERT INTO sources (id, git_url, branch, path, source_type, enabled, file_patterns)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'jaseci-docs',
            'https://github.com/jaseci-labs/jaseci.git',
            'main',
            'docs/docs',
            'docs',
            1,
            '*.md'
        ))
        conn.commit()

    def add(self, source: Source) -> Source:
        with self._get_conn() as conn:
            try:
                conn.execute('''
                    INSERT INTO sources (id, git_url, branch, path, source_type, enabled, file_patterns)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    source.id,
                    source.git_url,
                    source.branch,
                    source.path,
                    source.source_type.value,
                    1 if source.enabled else 0,
                    source.file_patterns
                ))
                conn.commit()
                return source
            except sqlite3.IntegrityError:
                raise ValueError(f"Source with id '{source.id}' already exists")

    def update(self, source_id: str, updates: dict) -> Source:
        source = self.get(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' not found")

        allowed_fields = {'git_url', 'branch', 'path', 'source_type', 'enabled', 'file_patterns'}
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}

        if 'source_type' in filtered and isinstance(filtered['source_type'], str):
            filtered['source_type'] = filtered['source_type']
        if 'enabled' in filtered:
            filtered['enabled'] = 1 if filtered['enabled'] else 0
        if 'file_patterns' in filtered and isinstance(filtered['file_patterns'], list):
            filtered['file_patterns'] = ','.join(filtered['file_patterns'])

        if not filtered:
            return source

        set_clause = ', '.join(f'{k} = ?' for k in filtered.keys())
        values = list(filtered.values()) + [source_id]

        with self._get_conn() as conn:
            conn.execute(f'UPDATE sources SET {set_clause} WHERE id = ?', values)
            conn.commit()

        return self.get(source_id)

    def delete(self, source_id: str):
        with self._get_conn() as conn:
            cursor = conn.execute('DELETE FROM sources WHERE id = ?', (source_id,))
            conn.commit()
            if cursor.rowcount == 0:
                raise ValueError(f"Source '{source_id}' not found")

    def get(self, source_id: str) -> Optional[Source]:
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT * FROM sources WHERE id = ?', (source_id,))
            row = cursor.fetchone()
            return Source.from_row(row) if row else None

    def list(self) -> list[Source]:
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT * FROM sources ORDER BY id')
            return [Source.from_row(row) for row in cursor.fetchall()]

    def get_enabled(self) -> list[Source]:
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT * FROM sources WHERE enabled = 1 ORDER BY id')
            return [Source.from_row(row) for row in cursor.fetchall()]

    def fetch_source(self, source: Source, out_dir: Path) -> dict:
        stats = {
            "source_id": source.id,
            "files": [],
            "total": 0,
            "errors": []
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=tmp_dir,
                    capture_output=True,
                    check=True
                )
                subprocess.run(
                    ["git", "remote", "add", "origin", source.git_url],
                    cwd=tmp_dir,
                    capture_output=True,
                    check=True
                )
                subprocess.run(
                    ["git", "config", "core.sparseCheckout", "true"],
                    cwd=tmp_dir,
                    capture_output=True,
                    check=True
                )

                sparse_file = tmp_dir / ".git" / "info" / "sparse-checkout"
                sparse_file.parent.mkdir(parents=True, exist_ok=True)
                sparse_file.write_text(f"{source.path}/*\n")

                result = subprocess.run(
                    ["git", "pull", "--depth=1", "origin", source.branch],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    stats["errors"].append(f"Git pull failed: {result.stderr}")
                    return stats

                source_dir = tmp_dir / source.path
                if not source_dir.exists():
                    source_dir = tmp_dir
                    for part in source.path.split('/'):
                        source_dir = source_dir / part
                        if not source_dir.exists():
                            break

                if not source_dir.exists():
                    stats["errors"].append(f"Path '{source.path}' not found in repo")
                    return stats

                source_out = out_dir / source.id
                source_out.mkdir(parents=True, exist_ok=True)

                for pattern in source.get_patterns_list():
                    for file_path in source_dir.rglob(pattern):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(source_dir)
                            dest = source_out / rel_path.name

                            if dest.exists():
                                stem = file_path.stem
                                parent = file_path.parent.name
                                dest = source_out / f"{parent}_{stem}{file_path.suffix}"

                            shutil.copy2(file_path, dest)
                            stats["files"].append({
                                "name": dest.name,
                                "size": dest.stat().st_size,
                                "type": file_path.suffix
                            })
                            stats["total"] += 1

            except subprocess.CalledProcessError as e:
                stats["errors"].append(f"Git command failed: {e}")
            except Exception as e:
                stats["errors"].append(str(e))

        return stats

    def fetch_all(self, out_dir: Path) -> dict:
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        results = {
            "sources": [],
            "total_files": 0,
            "total_errors": 0
        }

        for source in self.get_enabled():
            stats = self.fetch_source(source, out_dir)
            results["sources"].append(stats)
            results["total_files"] += stats["total"]
            results["total_errors"] += len(stats["errors"])

        return results

    def fetch_all_parallel(
        self,
        out_dir: Path,
        max_workers: int = 4,
        on_progress: Optional[Callable[[str, int, int], None]] = None
    ) -> dict:
        """Fetch from all enabled sources in parallel using ThreadPoolExecutor."""
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)

        sources = self.get_enabled()
        total = len(sources)
        results = {
            "sources": [],
            "total_files": 0,
            "total_errors": 0,
            "failed_sources": []
        }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {
                executor.submit(self.fetch_source, source, out_dir): source
                for source in sources
            }

            completed = 0
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                completed += 1
                try:
                    stats = future.result()
                    results["sources"].append(stats)
                    results["total_files"] += stats["total"]
                    results["total_errors"] += len(stats["errors"])
                except Exception as e:
                    results["failed_sources"].append({
                        "id": source.id,
                        "errors": [str(e)]
                    })
                    results["total_errors"] += 1

                if on_progress:
                    on_progress(source.id, completed, total)

        return results
