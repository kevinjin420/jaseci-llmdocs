import re
import yaml
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .llm import LLM
from .validator import Validator


class Merger:
    def __init__(self, llm: LLM, config: dict, on_progress=None):
        self.llm = llm
        self.on_progress = on_progress or (lambda *a: None)
        self.in_dir = Path(config.get('extraction', {}).get('output_dir', 'output/1_extracted'))
        self.out_dir = Path(config.get('merge', {}).get('output_dir', 'output/2_merged'))
        self.out_dir.mkdir(parents=True, exist_ok=True)

        self.validator = Validator(min_size_ratio=0.15, required_pattern_ratio=0.6)
        self.max_chunk_size = config.get('merge', {}).get('max_chunk_size', 15000)

        root = Path(__file__).parents[2]
        prompt_path = root / "config/merge_prompt.txt"
        if not prompt_path.exists():
            prompt_path = root / "config/stage2_merge_prompt.txt"
        with open(prompt_path) as f:
            self.prompt = f.read()
        with open(root / "config/topics.yaml") as f:
            self.topics = yaml.safe_load(f)['topics']

        self.completed = 0
        self.total = 0
        self.progress_lock = threading.Lock()

    def run(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        files = [f for f in self.in_dir.glob("*.md") if f.stat().st_size > 0]
        self.total = len(files)
        self.completed = 0

        self.on_progress(0, self.total, "Starting merge...")

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = {pool.submit(self.process, f): f for f in files}
            for future in as_completed(futures):
                future.result()
                with self.progress_lock:
                    self.completed += 1
                    self.on_progress(self.completed, self.total, futures[future].stem)

    def process(self, path: Path):
        topic = path.stem
        name = self.topics.get(topic, {}).get('name', topic)
        try:
            content = path.read_text().strip()
            merged = self.merge_content(content, name)
            if merged:
                result = self.validator.validate(content, merged)
                if not result.is_valid:
                    merged = self.fallback_merge(content)

                (self.out_dir / f"{topic}.txt").write_text(f"# {name}\n\n{merged}")
        except Exception:
            pass

    def merge_content(self, text: str, topic: str) -> str:
        if len(text) < 20000:
            return self.llm.query(text, f"Topic: {topic}\n\n{self.prompt}")

        chunks = self.smart_chunk(text)
        merged_parts = []

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(self.llm.query, chunk, f"Topic: {topic}\n\n{self.prompt}") for chunk in chunks]
            for f in futures:
                try:
                    result = f.result()
                    if result and result.strip():
                        merged_parts.append(result)
                except Exception:
                    pass

        if not merged_parts:
            return self.fallback_merge(text)

        return "\n\n".join(merged_parts)

    def smart_chunk(self, text: str) -> list:
        code_block_pattern = r'```[\s\S]*?```'
        code_blocks = []

        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        protected = re.sub(code_block_pattern, save_code_block, text)

        chunks = []
        current = []
        current_size = 0

        for part in re.split(r'(?=\n## )', protected):
            part_size = len(part)

            if current_size + part_size > self.max_chunk_size and current:
                chunk_text = "".join(current)
                chunks.append(self._restore_code_blocks(chunk_text, code_blocks))
                current = []
                current_size = 0

            current.append(part)
            current_size += part_size

        if current:
            chunk_text = "".join(current)
            chunks.append(self._restore_code_blocks(chunk_text, code_blocks))

        if len(chunks) == 1 and len(chunks[0]) > self.max_chunk_size:
            return self._split_preserving_code_blocks(text, code_blocks)

        return chunks

    def _restore_code_blocks(self, text: str, code_blocks: list) -> str:
        for i, block in enumerate(code_blocks):
            text = text.replace(f"__CODE_BLOCK_{i}__", block)
        return text

    def _split_preserving_code_blocks(self, text: str, code_blocks: list) -> list:
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            if para.startswith('```') or '```' in para:
                current.append(para)
                current_size += para_size
                continue

            if current_size + para_size > self.max_chunk_size and current:
                chunks.append("\n\n".join(current))
                current = []
                current_size = 0

            current.append(para)
            current_size += para_size

        if current:
            chunks.append("\n\n".join(current))

        return chunks if chunks else [text]

    def fallback_merge(self, text: str) -> str:
        lines = text.split('\n')
        seen = set()
        result = []

        for line in lines:
            normalized = line.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(line)
            elif not normalized:
                result.append(line)

        return '\n'.join(result)
