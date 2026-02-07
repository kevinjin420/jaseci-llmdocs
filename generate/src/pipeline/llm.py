import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Optional, Callable
from dotenv import load_dotenv

# Load .env
docgen_dir = Path(__file__).parents[2]
if (docgen_dir / ".env").exists(): load_dotenv(docgen_dir / ".env")

class LLM:
    APP_URL = "https://jaseci.org"
    APP_TITLE = "Jaseci DocGen"

    def __init__(self, config: Dict, stage_cfg: Dict = None):
        self.cfg = config['llm'].copy()
        if stage_cfg and 'llm' in stage_cfg:
            self.cfg.update(stage_cfg['llm'])

        self.key = os.environ.get(self.cfg.get('api_key_env', 'OPENROUTER_API_KEY'))
        if not self.key: raise ValueError("Missing API Key")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.APP_URL,
            "X-Title": self.APP_TITLE
        }

    def query(self, text: str, prompt_tpl: str = None) -> str:
        prompt = prompt_tpl.replace('{content}', text) if prompt_tpl else text
        data = {
            "model": self.cfg['model'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.cfg.get('temperature', 0.0)
        }
        if self.cfg.get('max_tokens'):
            data["max_tokens"] = self.cfg['max_tokens']
        if self.cfg.get('seed') is not None:
            data["seed"] = self.cfg['seed']

        for i in range(self.cfg.get('max_retries', 3)):
            try:
                res = requests.post(self.url, headers=self._headers(), json=data, timeout=120)
                if res.ok: return res.json()['choices'][0]['message']['content']
                if res.status_code in [500, 502, 503, 504, 429]:
                    time.sleep(2 ** i)
                    continue
                raise Exception(f"API Error {res.status_code}: {res.text}")
            except Exception as e:
                if i == self.cfg.get('max_retries', 3) - 1: raise e
                time.sleep(2 ** i)
        return ""

    def query_stream(
        self,
        text: str,
        prompt_tpl: str = None,
        on_token: Optional[Callable[[str], None]] = None
    ) -> str:
        """Query LLM with streaming response."""
        prompt = prompt_tpl.replace('{content}', text) if prompt_tpl else text
        data = {
            "model": self.cfg['model'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.cfg.get('temperature', 0.0),
            "stream": True
        }
        if self.cfg.get('max_tokens'):
            data["max_tokens"] = self.cfg['max_tokens']
        if self.cfg.get('seed') is not None:
            data["seed"] = self.cfg['seed']

        accumulated = []
        max_retries = self.cfg.get('max_retries', 3)

        for attempt in range(max_retries):
            try:
                with requests.post(
                    self.url, headers=self._headers(), json=data, stream=True, timeout=300
                ) as response:
                    if not response.ok:
                        if response.status_code in [500, 502, 503, 504, 429]:
                            time.sleep(2 ** attempt)
                            continue
                        raise Exception(f"API Error {response.status_code}")

                    for line in response.iter_lines():
                        if not line:
                            continue
                        line_text = line.decode('utf-8')
                        if not line_text.startswith('data: '):
                            continue
                        data_str = line_text[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                accumulated.append(content)
                                if on_token:
                                    on_token(content)
                        except json.JSONDecodeError:
                            continue
                    return ''.join(accumulated)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2 ** attempt)

        return ''.join(accumulated)
