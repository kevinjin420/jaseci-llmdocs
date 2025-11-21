"""LLM service for running benchmarks via OpenRouter API"""

import json
import os
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime

import openai

from database import BenchmarkResultService, DocumentationService


class LLMService:
    """Service for running LLM benchmarks via OpenRouter"""

    def __init__(self, tests_file: str = "tests.json"):
        self.tests = self._load_tests(tests_file)
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not found in environment")

        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/jaseci-llmdocs",
                "X-Title": "Jac LLM Benchmark"
            }
        )

    def _load_tests(self, tests_file: str) -> List[Dict]:
        with open(tests_file, 'r') as f:
            return json.load(f)

    def get_doc_content(self, variant: str) -> Optional[str]:
        """Fetch documentation content from URL via DocumentationService"""
        return DocumentationService.get_variant(variant)

    def fetch_available_models(self) -> List[Dict]:
        """Fetch available models from OpenRouter API"""
        import requests

        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            return []

        headers = {'Authorization': f'Bearer {api_key}'}

        try:
            response = requests.get('https://openrouter.ai/api/v1/models', headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"Warning: Failed to fetch models from OpenRouter: {e}")
            return []

    def get_available_variants(self) -> List[str]:
        """Get list of available documentation variants"""
        variants_data = DocumentationService.get_all_variants()
        return [v['name'] for v in variants_data]

    def _get_max_tokens_for_model(self, model_id: str) -> int:
        """Get appropriate max_tokens for a given model"""
        if 'haiku' in model_id.lower():
            return 8192
        elif 'claude' in model_id.lower():
            return 16000
        elif 'gemini' in model_id.lower():
            return 65536
        elif 'gpt-4o-mini' in model_id.lower():
            return 16000
        elif 'gpt-4o' in model_id.lower():
            return 16000
        elif 'o1' in model_id.lower():
            return 100000
        else:
            return 8192

    def _build_response_format(self, tests: List[Dict]) -> Dict:
        """Build JSON schema for structured output enforcement via OpenRouter"""
        properties = {
            test["id"]: {"type": "string"}
            for test in tests
        }
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "benchmark_responses",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": properties,
                    "required": [test["id"] for test in tests],
                    "additionalProperties": False
                }
            }
        }

    def _construct_prompt(self, doc_content: str, tests_to_use: List[Dict]) -> str:
        """Construct full prompt for LLM"""
        test_prompts = {
            "tests": [
                {
                    "id": test["id"],
                    "level": test["level"],
                    "category": test["category"],
                    "task": test["task"],
                    "points": test["points"],
                    "hints": test["hints"]
                }
                for test in tests_to_use
            ]
        }

        test_prompts_json = json.dumps(test_prompts, indent=2)

        prompt_template = """You are a Jac programming language expert. Write valid Jac code for each test case based on the documentation.

# Documentation
{doc_content}

# Test Cases
{test_prompts_json}

# Task
Return a JSON object mapping each test ID to Jac code. Use \\n for newlines and \\" for quotes in the code strings.
"""
        return prompt_template.format(
            doc_content=doc_content,
            test_prompts_json=test_prompts_json
        )
    def run_benchmark(
        self,
        model_id: str,
        variant: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        test_limit: Optional[int] = None
    ) -> Dict:
        """Run single-call benchmark"""
        if temperature is None:
            temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.1'))
        if max_tokens is None:
            max_tokens = self._get_max_tokens_for_model(model_id)

        doc_content = self.get_doc_content(variant)
        if not doc_content:
            raise ValueError(f"No documentation content found for variant '{variant}'")

        tests_to_use = self.tests[:test_limit] if test_limit else self.tests
        prompt = self._construct_prompt(doc_content, tests_to_use)

        max_retries = 3
        retry_delay = 20

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(retry_delay)
                response = self.client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=self._build_response_format(tests_to_use)
                )
                response_text = response.choices[0].message.content.strip()
                break
            except Exception as e:
                if '429' in str(e) and attempt < max_retries - 1:
                    retry_delay *= 2
                else:
                    raise

        responses = json.loads(response_text)

        test_suite_type = "small" if test_limit else "full"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_id.replace('/', '-')
        run_id = f"{safe_model_name}-{variant}-{test_suite_type}-{timestamp}"

        BenchmarkResultService.create(
            run_id=run_id,
            model=model_id,
            model_id=model_id,
            variant=variant,
            temperature=temperature,
            max_tokens=max_tokens,
            test_limit=test_limit,
            test_suite=test_suite_type,
            total_tests=len(tests_to_use),
            responses=responses
        )

        return {
            'run_id': run_id,
            'model': model_id,
            'variant': variant,
            'num_responses': len(responses),
            'test_suite': test_suite_type,
            'responses': responses
        }

    def run_benchmark_concurrent(
        self,
        model_id: str,
        variant: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        test_limit: Optional[int] = None,
        batch_size: int = 45,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """Run batched benchmark"""
        if temperature is None:
            temperature = float(os.getenv('DEFAULT_TEMPERATURE', '0.1'))
        if max_tokens is None:
            max_tokens = self._get_max_tokens_for_model(model_id)

        doc_content = self.get_doc_content(variant)
        if not doc_content:
            raise ValueError(f"No documentation content found for variant '{variant}'")

        tests_to_use = self.tests[:test_limit] if test_limit else self.tests
        num_batches = (len(tests_to_use) + batch_size - 1) // batch_size
        responses = {}

        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(tests_to_use))
            batch = tests_to_use[start_idx:end_idx]

            if progress_callback:
                progress_callback(start_idx, len(tests_to_use), f"Batch {batch_num + 1}/{num_batches}",
                                batch_num=batch_num + 1, num_batches=num_batches)

            max_retries = 2
            for retry in range(max_retries + 1):
                try:
                    if retry > 0:
                        time.sleep(2 ** retry)
                    prompt = self._construct_prompt(doc_content, batch)
                    response = self.client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format=self._build_response_format(batch)
                    )
                    response_text = response.choices[0].message.content.strip()
                    batch_responses = json.loads(response_text)
                    responses.update(batch_responses)
                    break
                except Exception as e:
                    if retry >= max_retries:
                        raise

        if progress_callback:
            progress_callback(len(tests_to_use), len(tests_to_use), "Completed")

        if not responses:
            raise RuntimeError("No responses generated - all batches failed")

        test_suite_type = "small" if test_limit else "full"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_model_name = model_id.replace('/', '-')
        run_id = f"{safe_model_name}-{variant}-{test_suite_type}-{timestamp}"

        BenchmarkResultService.create(
            run_id=run_id,
            model=model_id,
            model_id=model_id,
            variant=variant,
            temperature=temperature,
            max_tokens=max_tokens,
            test_limit=test_limit,
            test_suite=test_suite_type,
            total_tests=len(tests_to_use),
            responses=responses,
            batch_size=batch_size,
            num_batches=num_batches
        )

        return {
            'run_id': run_id,
            'model': model_id,
            'variant': variant,
            'num_responses': len(responses),
            'test_suite': test_suite_type,
            'responses': responses
        }