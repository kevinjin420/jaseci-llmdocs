import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class DocSection:
    file_path: str
    section_title: str
    content: str
    start_line: int
    end_line: int
    level: int


@dataclass
class DocFile:
    file_path: str
    relative_path: str
    category: str
    sections: List[DocSection]
    total_lines: int
    total_chars: int


class DocumentParser:
    def __init__(self, source_dir: str, skip_patterns: List[str] = None):
        self.source_dir = Path(source_dir)
        self.skip_patterns = skip_patterns or []

    def should_skip(self, file_path: Path) -> bool:
        for pattern in self.skip_patterns:
            if file_path.match(pattern):
                return True
        return False

    def collect_markdown_files(self) -> List[Path]:
        md_files = []
        for md_file in self.source_dir.rglob("*.md"):
            if not self.should_skip(md_file):
                md_files.append(md_file)
        return sorted(md_files)

    def extract_sections(self, content: str, file_path: str) -> List[DocSection]:
        lines = content.split('\n')
        sections = []
        current_section = None
        current_content = []
        current_start = 0

        for i, line in enumerate(lines, 1):
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    current_section.end_line = i - 1
                    sections.append(current_section)

                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                current_section = DocSection(
                    file_path=file_path,
                    section_title=title,
                    content="",
                    start_line=i,
                    end_line=i,
                    level=level
                )
                current_content = [line]
                current_start = i
            elif current_section:
                current_content.append(line)
            else:
                if not current_section and line.strip():
                    current_section = DocSection(
                        file_path=file_path,
                        section_title="[Preamble]",
                        content="",
                        start_line=1,
                        end_line=1,
                        level=0
                    )
                    current_content = [line]

        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            current_section.end_line = len(lines)
            sections.append(current_section)

        return sections

    def parse_file(self, file_path: Path) -> DocFile:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        relative_path = str(file_path.relative_to(self.source_dir))
        category = relative_path.split('/')[0] if '/' in relative_path else 'root'

        sections = self.extract_sections(content, str(file_path))

        return DocFile(
            file_path=str(file_path),
            relative_path=relative_path,
            category=category,
            sections=sections,
            total_lines=len(content.split('\n')),
            total_chars=len(content)
        )

    def chunk_section(self, section: DocSection, max_lines: int = 500) -> List[DocSection]:
        lines = section.content.split('\n')

        if len(lines) <= max_lines:
            return [section]

        chunks = []
        current_chunk_lines = []
        chunk_start = section.start_line

        for i, line in enumerate(lines):
            current_chunk_lines.append(line)

            if len(current_chunk_lines) >= max_lines:
                chunk_content = '\n'.join(current_chunk_lines)
                chunk = DocSection(
                    file_path=section.file_path,
                    section_title=f"{section.section_title} [Part {len(chunks) + 1}]",
                    content=chunk_content,
                    start_line=chunk_start,
                    end_line=chunk_start + len(current_chunk_lines) - 1,
                    level=section.level
                )
                chunks.append(chunk)
                current_chunk_lines = []
                chunk_start += len(current_chunk_lines)

        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunk = DocSection(
                file_path=section.file_path,
                section_title=f"{section.section_title} [Part {len(chunks) + 1}]",
                content=chunk_content,
                start_line=chunk_start,
                end_line=section.end_line,
                level=section.level
            )
            chunks.append(chunk)

        return chunks

    def parse_all(self, categories: List[str] = None) -> List[DocFile]:
        files = self.collect_markdown_files()
        doc_files = []

        for file_path in files:
            doc_file = self.parse_file(file_path)

            if categories and doc_file.category not in categories:
                continue

            doc_files.append(doc_file)

        return doc_files

    def get_statistics(self, doc_files: List[DocFile]) -> Dict:
        total_files = len(doc_files)
        total_sections = sum(len(df.sections) for df in doc_files)
        total_lines = sum(df.total_lines for df in doc_files)
        total_chars = sum(df.total_chars for df in doc_files)

        categories = {}
        for df in doc_files:
            if df.category not in categories:
                categories[df.category] = 0
            categories[df.category] += 1

        return {
            'total_files': total_files,
            'total_sections': total_sections,
            'total_lines': total_lines,
            'total_chars': total_chars,
            'estimated_tokens': total_chars // 4,
            'categories': categories
        }
