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

        # Load format prompt (changed from ultra_compression to format)
        prompt_path = config.get('prompts', {}).get('format', 'config/format_prompt.txt')
        prompt_file = Path(__file__).parent.parent / prompt_path
        with open(prompt_file, 'r') as f:
            self.format_prompt = f.read()

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (chars // 4)"""
        return len(text) // 4

    def final_cleanup(self, content: str) -> str:
        """
        Final cleanup step: strip all unnecessary whitespace and newlines.

        This creates the most compact possible output by:
        - Removing all newlines
        - Collapsing multiple spaces to single space
        - Stripping leading/trailing whitespace

        Args:
            content: Content to clean up

        Returns:
            Ultra-compact content with minimal whitespace
        """
        import re

        # Replace all newlines with spaces
        content = content.replace('\n', ' ')

        # Replace all tabs with spaces
        content = content.replace('\t', ' ')

        # Collapse multiple spaces into single space
        content = re.sub(r'\s+', ' ', content)

        # Strip leading and trailing whitespace
        content = content.strip()

        return content

    def format_content(self, content: str, name: str = "documentation") -> CompressionResult:
        """
        Format documentation into compact reference style.

        NOTE: This only formats/compacts, it does NOT remove information.

        Args:
            content: The merged documentation content
            name: Name for this compression task

        Returns:
            CompressionResult with formatted content and metrics
        """
        print(f"\nFormatting: {name}")

        original_tokens = self._estimate_tokens(content)
        print(f"  Input: {original_tokens:,} tokens")

        # Build prompt with format template
        prompt = self.format_prompt.replace("{content}", content)

        try:
            # Use the condenser's OpenRouter API
            formatted_content = self.condenser.condense_with_openrouter(content, prompt)

            formatted_tokens = self._estimate_tokens(formatted_content)
            compression_ratio = 1 - (formatted_tokens / original_tokens) if original_tokens > 0 else 0

            print(f"  Output: {formatted_tokens:,} tokens ({compression_ratio:.1%} reduction)")

            return CompressionResult(
                original_tokens=original_tokens,
                compressed_tokens=formatted_tokens,
                compression_ratio=compression_ratio,
                content=formatted_content,
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

    def format_file(self, input_path: Path, output_path: Path) -> CompressionResult:
        """
        Format a single file to compact reference style.

        Args:
            input_path: Path to input merged document
            output_path: Path to save formatted output

        Returns:
            CompressionResult with metrics
        """
        # Read input
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Format
        result = self.format_content(content, input_path.name)

        # Write output
        if result.success:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.content)
            print(f"  Saved: {output_path}")

        return result

    def regex_format(self, content: str) -> str:
        """
        Apply regex-based formatting without LLM call.

        Applies compact formatting using pattern matching:
        - Remove excessive whitespace
        - Condense common patterns
        - No LLM API call needed
        """
        import re

        # Remove markdown bold/italic (keep content)
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # **bold** -> bold
        content = re.sub(r'\*([^*]+)\*', r'\1', content)      # *italic* -> italic
        content = re.sub(r'__([^_]+)__', r'\1', content)      # __bold__ -> bold
        content = re.sub(r'_([^_]+)_', r'\1', content)        # _italic_ -> italic

        # Condense headers to inline format
        content = re.sub(r'^#+\s+(.+)$', r'\1:', content, flags=re.MULTILINE)

        # Remove extra blank lines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        # Clean up list markers
        content = re.sub(r'^\s*[-*]\s+', '• ', content, flags=re.MULTILINE)

        return content

    def combine_and_format_topics(self, topics_dir: Path, output_file: Path) -> CompressionResult:
        """
        Combine all topic files and format into single final document.

        Args:
            topics_dir: Directory containing topic files
            output_file: Output path for final combined document

        Returns:
            CompressionResult with metrics
        """
        import yaml

        # Load topics config for ordering
        topics_path = Path(__file__).parent.parent / "config" / "topics.yaml"
        with open(topics_path, 'r') as f:
            topics_config = yaml.safe_load(f)['topics']

        print(f"\n{'='*80}")
        print(f"STAGE 3: FORMATTING AND COMBINING TOPICS")
        print(f"{'='*80}")

        # Read all topic files
        topic_contents = {}
        for topic_id in topics_config.keys():
            topic_file = topics_dir / f"{topic_id}.txt"
            if topic_file.exists():
                with open(topic_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        topic_contents[topic_id] = content

        if not topic_contents:
            return CompressionResult(
                original_tokens=0,
                compressed_tokens=0,
                compression_ratio=0,
                content="",
                success=False,
                error="No topic files found"
            )

        print(f"  Topics found: {len(topic_contents)}")

        # Combine topics in order (preserving topic structure)
        combined_parts = []
        for topic_id, content in topic_contents.items():
            combined_parts.append(content)

        combined_content = "\n\n".join(combined_parts)
        original_tokens = self._estimate_tokens(combined_content)
        print(f"  Combined size: {original_tokens:,} tokens")

        # Apply regex-based formatting (NO LLM CALL)
        print(f"\nApplying regex-based formatting (no LLM call)...")
        formatted_content = self.regex_format(combined_content)
        after_format_tokens = self._estimate_tokens(formatted_content)
        print(f"  After formatting: {after_format_tokens:,} tokens")

        # Apply final cleanup to remove all unnecessary whitespace and newlines
        print(f"\nApplying final cleanup (removing whitespace and newlines)...")
        cleaned_content = self.final_cleanup(formatted_content)
        final_tokens = self._estimate_tokens(cleaned_content)

        print(f"  After cleanup: {final_tokens:,} tokens")
        print(f"  Total reduction: {1 - (final_tokens / original_tokens):.1%}")

        result = CompressionResult(
            original_tokens=original_tokens,
            compressed_tokens=final_tokens,
            compression_ratio=1 - (final_tokens / original_tokens),
            content=cleaned_content,
            success=True
        )

        # Write output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.content)
        print(f"\nFinal document saved: {output_file}")
        print(f"{'='*80}\n")

        return result


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

    # Format
    result = compressor.format_content(content, name=input_file.name)

    # Write output
    if result.success:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.content)
        print(f"Output saved to: {output_file}")
    else:
        print(f"Formatting failed: {result.error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
