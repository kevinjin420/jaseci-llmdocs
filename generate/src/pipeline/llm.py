import os
import time
import requests
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# Load .env
docgen_dir = Path(__file__).parents[2]
if (docgen_dir / ".env").exists(): load_dotenv(docgen_dir / ".env")

class LLM:
    def __init__(self, config: Dict, stage_cfg: Dict = None):
        self.cfg = config['llm'].copy()
        if stage_cfg and 'llm' in stage_cfg:
            self.cfg.update(stage_cfg['llm'])
        
        self.key = os.environ.get(self.cfg.get('api_key_env', 'OPENROUTER_API_KEY'))
        if not self.key: raise ValueError("Missing API Key")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def query(self, text: str, prompt_tpl: str = None) -> str:
        prompt = prompt_tpl.replace('{content}', text) if prompt_tpl else text
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        data = {
            "model": self.cfg['model'],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.cfg.get('max_tokens', 4096),
            "temperature": self.cfg.get('temperature', 0.0)
        }

        for i in range(self.cfg.get('max_retries', 3)):
            try:
                res = requests.post(self.url, headers=headers, json=data, timeout=120)
                if res.ok: return res.json()['choices'][0]['message']['content']
                if res.status_code in [500, 502, 503, 504, 429]:
                    time.sleep(2 ** i)
                    continue
                raise Exception(f"API Error {res.status_code}: {res.text}")
            except Exception as e:
                if i == self.cfg.get('max_retries', 3) - 1: raise e
                time.sleep(2 ** i)
        return ""
