import os
import re
import time
import requests
from typing import Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)


@dataclass
class CondensationResult:
    original_content: str
    condensed_content: str
    original_tokens: int
    condensed_tokens: int
    compression_ratio: float
    processing_time: float
    success: bool
    error: Optional[str] = None


class LLMCondenser:
    def __init__(self, config: Dict):
        self.config = config
        self.llm_config = config['llm']
        # Make condensation_config optional for new topic-based pipeline
        self.condensation_config = config.get('condensation', {})
        self.provider = self.llm_config['provider']

        api_key_env = self.llm_config.get('api_key_env', 'OPENROUTER_API_KEY')
        self.api_key = os.environ.get(api_key_env)

        if not self.api_key:
            raise ValueError(f"API key not found in environment variable: {api_key_env}")

        if self.provider == 'openrouter':
            self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Load condensation prompt from config (optional, for backward compatibility)
        prompt_path = config.get('prompts', {}).get('condensation', 'config/condensation_prompt.txt')
        prompt_file = Path(__file__).parent.parent / prompt_path
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                self.prompt_template = f.read()
        else:
            self.prompt_template = ""

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def strip_html(self, content: str) -> str:
        content = re.sub(r'<div[^>]*>', '', content)
        content = re.sub(r'</div>', '', content)
        content = re.sub(r'class="[^"]*"', '', content)
        content = re.sub(r'<[^>]+>', '', content)
        return content

    def preprocess(self, content: str) -> str:
        if self.condensation_config.get('strip_html', True):
            content = self.strip_html(content)

        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()

        return content

    def condense_with_openrouter(self, content: str, custom_prompt: str = None) -> str:
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self.prompt_template.replace('{content}', content)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/jaseci-llmdocs",
            "X-Title": "JAC LLM Docs Pipeline"
        }

        data = {
            "model": self.llm_config['model'],
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "max_tokens": self.llm_config.get('max_tokens', 4096),
            "temperature": self.llm_config.get('temperature', 0.0)
        }

        # Retry configuration
        max_retries = self.llm_config.get('max_retries', 3)
        retry_delay = self.llm_config.get('retry_delay', 2)
        retryable_codes = [500, 502, 503, 504, 429]

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.openrouter_url,
                    headers=headers,
                    json=data,
                    timeout=120
                )

                if not response.ok:
                    error_detail = response.text
                    status_code = response.status_code

                    # Check if this is a retryable error
                    if status_code in retryable_codes and attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"  OpenRouter API error ({status_code}), retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"OpenRouter API error ({status_code}): {error_detail}")

                result = response.json()
                return result['choices'][0]['message']['content']

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"  OpenRouter request error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"OpenRouter API error: {str(e)}")
            except (KeyError, IndexError) as e:
                raise Exception(f"OpenRouter response parsing error: {str(e)}, Response: {result}")

        raise Exception(f"OpenRouter API failed after {max_retries} attempts")

    def condense(self, content: str, section_title: str = "") -> CondensationResult:
        start_time = time.time()

        try:
            preprocessed = self.preprocess(content)
            original_tokens = self.estimate_tokens(content)

            condensed = self.condense_with_openrouter(preprocessed)

            condensed_tokens = self.estimate_tokens(condensed)
            compression_ratio = condensed_tokens / original_tokens if original_tokens > 0 else 0
            processing_time = time.time() - start_time

            return CondensationResult(
                original_content=content,
                condensed_content=condensed,
                original_tokens=original_tokens,
                condensed_tokens=condensed_tokens,
                compression_ratio=compression_ratio,
                processing_time=processing_time,
                success=True
            )

        except Exception as e:
            return CondensationResult(
                original_content=content,
                condensed_content="",
                original_tokens=self.estimate_tokens(content),
                condensed_tokens=0,
                compression_ratio=0.0,
                processing_time=time.time() - start_time,
                success=False,
                error=str(e)
            )

    def validate_result(self, result: CondensationResult) -> bool:
        if not result.success:
            return False

        # Make validation config optional
        validation_config = self.config.get('validation', {})
        min_ratio = validation_config.get('min_ratio', 0.15)
        max_ratio = validation_config.get('max_ratio', 0.5)

        if result.compression_ratio < min_ratio or result.compression_ratio > max_ratio:
            return False

        if len(result.condensed_content.strip()) == 0:
            return False

        return True

    def condense_text(self, content: str, custom_prompt: str) -> str:
        """
        Simple wrapper for topic-based pipeline.
        Takes content and a custom prompt, returns condensed text.
        """
        return self.condense_with_openrouter(content, custom_prompt)

    def format_output(self, condensed: str, section_title: str = "") -> str:
        output_format = self.condensation_config.get('output_format', 'plain_text')

        if output_format == 'plain_text':
            if section_title:
                return f"## {section_title}\n\n{condensed}\n"
            return condensed

        elif output_format == 'markdown_minimal':
            if section_title:
                return f"## {section_title}\n\n{condensed}\n"
            return condensed

        return condensed
