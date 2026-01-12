import re
import yaml
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .llm import LLM


class Extractor:
    def __init__(self, llm: LLM, config: dict, on_progress=None):
        self.llm = llm
        self.cfg = config
        self.on_progress = on_progress or (lambda *a: None)
        self.out_dir = Path(config.get('extraction', {}).get('output_dir', 'output/1_extracted'))
        self.out_dir.mkdir(parents=True, exist_ok=True)

        root = Path(__file__).parents[2]
        with open(root / "config/topics.yaml") as f: self.topics = yaml.safe_load(f)['topics']
        with open(root / "config/stage1_extract_prompt.txt") as f: self.prompt = f.read()

        self.locks = {k: threading.Lock() for k in self.topics}
        self.files = {k: self.out_dir / f"{k}.md" for k in self.topics}
        self.completed = 0
        self.total = 0
        self.progress_lock = threading.Lock()

    def run(self, src_dir: Path, skip: list = None):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        for f in self.files.values():
            with open(f, 'w') as d: d.write(f"# {f.stem}\n\n")

        files = [f for f in src_dir.glob('**/*.md') if not any(f.match(p) for p in (skip or []))]
        self.total = len(files)
        self.completed = 0

        self.on_progress(0, self.total, "Starting extraction...")

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = {pool.submit(self.process, f): f for f in files}
            for future in as_completed(futures):
                future.result()
                with self.progress_lock:
                    self.completed += 1
                    self.on_progress(self.completed, self.total, futures[future].name)

    def process(self, path: Path):
        try:
            text = path.read_text()
            if not text.strip(): return

            hits = [k for k, v in self.topics.items() if any(w in text.lower() for w in v.get('keywords', []))][:15]
            if not hits: return

            topics_list = "\n".join([f"- {k}" for k in hits])
            res = self.llm.query(text, self.prompt.replace("{topics}", topics_list))

            curr_topic, buf = None, []
            for line in res.split('\n'):
                m = re.match(r'===TOPIC:\s*(.+)===', line)
                if m:
                    self._save(curr_topic, buf, path.name)
                    curr_topic, buf = m.group(1).split('(')[0].strip(), []
                else:
                    buf.append(line)
            self._save(curr_topic, buf, path.name)
        except Exception:
            pass

    def _save(self, topic, lines, fname):
        if topic in self.files and lines:
            content = '\n'.join(lines).strip()
            if len(content) > 50:
                with self.locks[topic], open(self.files[topic], 'a') as f:
                    f.write(f"\n## From: {fname}\n\n{content}\n\n")
