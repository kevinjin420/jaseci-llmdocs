#!/usr/bin/env python3
"""Size controller for LLM outputs.

Enforces output size bounds with retry logic and prompt adjustment.
"""
from dataclasses import dataclass


@dataclass
class SizeResult:
    content: str
    attempts: int
    within_bounds: bool
    final_size: int


class SizeController:
    PRESERVE_MORE_SUFFIX = """

IMPORTANT: Your previous response was too short. You MUST include more detail.
- Keep ALL code examples
- Keep ALL syntax patterns
- Keep ALL API signatures
- Only compress explanatory prose
"""

    COMPRESS_MORE_SUFFIX = """

IMPORTANT: Your previous response was too long. Compress more aggressively:
- Remove redundant explanations
- Keep only the most essential code examples
- Combine similar concepts
"""

    def __init__(self, llm, validator=None):
        self.llm = llm
        self.validator = validator

    def query_with_bounds(self, content, prompt, min_chars=None, max_chars=None,
                          max_retries=3, context=""):
        """Query LLM with size bounds enforcement.

        Args:
            content: Input content to process
            prompt: Base prompt for LLM
            min_chars: Minimum output character count (None = no minimum)
            max_chars: Maximum output character count (None = no maximum)
            max_retries: Maximum retry attempts
            context: Additional context (e.g., topic name)

        Returns:
            SizeResult with content and metadata
        """
        best_result = None
        best_score = -1

        for attempt in range(max_retries + 1):
            adjusted_prompt = prompt

            if attempt > 0 and best_result:
                if min_chars and len(best_result) < min_chars:
                    adjusted_prompt = prompt + self.PRESERVE_MORE_SUFFIX
                elif max_chars and len(best_result) > max_chars:
                    adjusted_prompt = prompt + self.COMPRESS_MORE_SUFFIX

            full_prompt = f"{context}\n\n{adjusted_prompt}" if context else adjusted_prompt
            result = self.llm.query(content, full_prompt)

            if not result or not result.strip():
                continue

            result_len = len(result)
            within_bounds = True

            if min_chars and result_len < min_chars:
                within_bounds = False
            if max_chars and result_len > max_chars:
                within_bounds = False

            score = self._score_result(result, min_chars, max_chars)
            if score > best_score:
                best_score = score
                best_result = result

            if within_bounds:
                return SizeResult(
                    content=result,
                    attempts=attempt + 1,
                    within_bounds=True,
                    final_size=result_len
                )

        return SizeResult(
            content=best_result or "",
            attempts=max_retries + 1,
            within_bounds=False,
            final_size=len(best_result) if best_result else 0
        )

    def _score_result(self, result, min_chars, max_chars):
        """Score result based on how close it is to target range."""
        result_len = len(result)

        if min_chars and max_chars:
            target = (min_chars + max_chars) / 2
            distance = abs(result_len - target)
            max_distance = max(target - min_chars, max_chars - target)
            return 1 - (distance / max_distance) if max_distance > 0 else 1

        if min_chars:
            return min(result_len / min_chars, 1.0)

        if max_chars:
            return min(max_chars / result_len, 1.0) if result_len > 0 else 0

        return 1.0
