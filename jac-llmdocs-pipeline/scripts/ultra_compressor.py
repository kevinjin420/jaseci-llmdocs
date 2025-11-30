"""
Ultra-compression stage: Convert merged docs into mini-doc reference format.

This stage takes the merged documentation and applies aggressive compression
to produce an ultra-dense quick reference format similar to mini_v3.
"""

import os
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

from condenser import LLMCondenser, CondensationResult


@dataclass
class CompressionResult:
    """Result of ultra-compression"""
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    content: str
    success: bool
    error: str = None


class UltraCompressor:
    """
    Final compression stage to create reference-format documentation.

    Uses a special reference-format prompt to create ultra-dense,
    quick-reference style documentation optimized for LLM code generation.
    """

    def __init__(self, condenser: LLMCondenser, config: Dict):
        """
        Initialize ultra-compressor.

        Args:
            condenser: LLMCondenser instance for LLM API calls
            config: Configuration dictionary with prompts paths
        """
        self.condenser = condenser
        self.config = config

        # Load ultra-compression prompt from config
        prompt_path = config.get('prompts', {}).get('ultra_compression', 'config/reference_format_prompt.txt')
        prompt_file = Path(__file__).parent.parent / prompt_path
        with open(prompt_file, 'r') as f:
            self.reference_prompt = f.read()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (chars // 4)"""
        return len(text) // 4

    def compress(self, content: str, name: str = "documentation") -> CompressionResult:
        """
        Apply ultra-compression to create reference-format docs.

        Args:
            content: The merged documentation content
            name: Name for this compression task

        Returns:
            CompressionResult with compressed content and metrics
        """
        print(f"\nUltra-compressing: {name}")

        original_tokens = self._estimate_tokens(content)
        print(f"  Input: {original_tokens:,} tokens")

        # Build prompt with reference format template
        prompt = self.reference_prompt.replace("{content}", content)

        try:
            # Use the condenser's OpenRouter API
            compressed_content = self.condenser.condense_with_openrouter(content, prompt)

            compressed_tokens = self._estimate_tokens(compressed_content)
            compression_ratio = 1 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0

            print(f"  Output: {compressed_tokens:,} tokens ({compression_ratio:.1%} reduction)")

            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=compression_ratio,
                content=compressed_content,
                success=True
            )

        except Exception as e:
            print(f"  Error: {str(e)}")
            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=0,
                compression_ratio=0,
                content="",
                success=False,
                error=str(e)
            )

    def compress_file(self, input_path: Path, output_path: Path) -> CompressionResult:
        """
        Compress a single file to reference format.

        Args:
            input_path: Path to input merged document
            output_path: Path to save ultra-compressed output

        Returns:
            CompressionResult with metrics
        """
        # Read input
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Compress
        result = self.compress(content, input_path.name)

        # Write output
        if result.success:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.content)
            print(f"  Saved: {output_path}")

        return result

    def multi_pass_compress(
        self,
        content: str,
        passes: int = 2,
        name: str = "documentation"
    ) -> CompressionResult:
        """
        Apply multiple compression passes for maximum density.

        Each pass further abbreviates and condenses the output.

        Args:
            content: Input content
            passes: Number of compression passes (default 2)
            name: Name for logging

        Returns:
            Final CompressionResult
        """
        print(f"\n{'='*80}")
        print(f"ULTRA-COMPRESSION: {passes} passes")
        print(f"{'='*80}")

        current_content = content
        original_tokens = self._estimate_tokens(content)

        for pass_num in range(1, passes + 1):
            print(f"\n--- Pass {pass_num}/{passes} ---")
            result = self.compress(current_content, f"{name} (pass {pass_num})")

            if not result.success:
                print(f"Pass {pass_num} failed: {result.error}")
                return result

            current_content = result.content

        # Final metrics
        final_tokens = self._estimate_tokens(current_content)
        final_ratio = 1 - (final_tokens / original_tokens) if original_tokens > 0 else 0

        print(f"\n{'='*80}")
        print(f"ULTRA-COMPRESSION COMPLETE")
        print(f"  Original: {original_tokens:,} tokens")
        print(f"  Final: {final_tokens:,} tokens")
        print(f"  Total reduction: {final_ratio:.1%}")
        print(f"{'='*80}\n")

        return CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=final_tokens,
            compression_ratio=final_ratio,
            content=current_content,
            success=True
        )


def main():
    """Standalone ultra-compression CLI"""
    import sys
    import yaml

    if len(sys.argv) < 2:
        print("Usage: python ultra_compressor.py <input_file> [output_file] [--passes N]")
        print("\nCompress merged documentation into ultra-dense reference format.")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    # Determine output file
    if len(sys.argv) >= 3 and not sys.argv[2].startswith('--'):
        output_file = Path(sys.argv[2])
    else:
        output_file = input_file.parent / f"{input_file.stem}_ultra{input_file.suffix}"

    # Check for --passes flag
    passes = 2
    if '--passes' in sys.argv:
        idx = sys.argv.index('--passes')
        if idx + 1 < len(sys.argv):
            passes = int(sys.argv[idx + 1])

    # Load config
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize condenser
    condenser = LLMCondenser(config)

    # Initialize ultra-compressor
    compressor = UltraCompressor(condenser, config)

    # Read input
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Compress
    result = compressor.multi_pass_compress(content, passes=passes, name=input_file.name)

    # Write output
    if result.success:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.content)
        print(f"Output saved to: {output_file}")
    else:
        print(f"Compression failed: {result.error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
