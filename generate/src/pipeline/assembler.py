"""
Single-pass LLM assembler for Jac documentation.

Stage 2 of the lossless pipeline: assembles final reference from extracted content.
Uses ONE LLM call with template-driven structure.
"""

from pathlib import Path
from .llm import LLM
from .deterministic_extractor import DeterministicExtractor, ExtractedContent
from .validator import Validator


class Assembler:
    """Assembles final reference document from extracted content."""

    def __init__(self, llm: LLM, config: dict, on_progress=None, on_token=None):
        self.llm = llm
        self.config = config
        self.on_progress = on_progress or (lambda *a: None)
        self.on_token = on_token
        self.validator = Validator()

        root = Path(__file__).parents[2]
        prompt_path = root / "config" / "assembly_prompt.txt"
        with open(prompt_path) as f:
            self.prompt_template = f.read()

    def assemble(self, extracted: ExtractedContent, extractor: DeterministicExtractor) -> str:
        """Assemble final document from extracted content in single LLM call."""

        self.on_progress(0, 3, "Formatting extracted content...")

        # Format content for LLM
        formatted_content = extractor.format_for_assembly(extracted)

        self.on_progress(1, 3, "Assembling with LLM (single pass)...")

        # Single LLM call (with optional streaming)
        prompt = self.prompt_template.replace("{content}", formatted_content)
        if self.on_token:
            result = self.llm.query_stream(formatted_content, prompt, on_token=self.on_token)
        else:
            result = self.llm.query(formatted_content, prompt)

        if not result:
            raise RuntimeError("LLM assembly failed - no output")

        self.on_progress(2, 3, "Validating output...")

        # Validate
        validation = self.validator.validate_final(result)
        if not validation.is_valid:
            print(f"Warning: Validation issues: {validation.issues}")
            if validation.missing_patterns:
                print(f"Missing patterns: {validation.missing_patterns[:5]}")

        self.on_progress(3, 3, "Assembly complete")

        return result


class LosslessPipeline:
    """
    Two-stage lossless pipeline:
    1. Deterministic extraction (no LLM)
    2. Single-pass LLM assembly
    """

    def __init__(self, config_path: Path):
        import yaml
        self.root = Path(__file__).parents[2]

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.extractor = DeterministicExtractor(self.config)
        self.llm = LLM(self.config, self.config.get('assembly', {}))
        self.assembler = Assembler(self.llm, self.config)
        self.validator = Validator()

    def run(self, source_dir: Path = None, output_path: Path = None) -> dict:
        """Execute the two-stage pipeline."""

        if source_dir is None:
            source_dir = self.root / "output" / "0_sanitized"
        if output_path is None:
            output_path = self.root / "output" / "reference.txt"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        print("=" * 50)
        print("Lossless Documentation Pipeline")
        print("=" * 50)

        # Stage 1: Deterministic extraction
        print("\nStage 1: Deterministic Extraction")
        print("-" * 30)

        extracted = self.extractor.extract_from_directory(source_dir)

        print(f"  Signatures extracted: {extracted.total_signatures}")
        print(f"  Examples extracted: {extracted.total_examples}")
        print(f"  Keywords found: {len(extracted.keywords_found)}")

        # Show distribution
        print("\n  By construct type:")
        for ct, examples in sorted(extracted.examples.items(), key=lambda x: -len(x[1])):
            if examples:
                print(f"    {ct}: {len(examples)} examples")

        # Stage 2: Single-pass assembly
        print("\nStage 2: LLM Assembly (single pass)")
        print("-" * 30)

        result = self.assembler.assemble(extracted, self.extractor)

        # Save result
        output_path.write_text(result)

        # Also save to release
        release_dir = self.root.parent / "release"
        release_dir.mkdir(exist_ok=True)
        (release_dir / "candidate.txt").write_text(result)

        # Stats
        input_size = sum(f.stat().st_size for f in source_dir.glob("*.md"))
        output_size = len(result)

        print(f"\n  Input: {input_size:,} bytes ({len(list(source_dir.glob('*.md')))} files)")
        print(f"  Output: {output_size:,} bytes")
        print(f"  Compression: {input_size/output_size:.1f}x")

        # Validate
        validation = self.validator.validate_final(result)
        print(f"\n  Validation: {'PASSED' if validation.is_valid else 'FAILED'}")
        if validation.missing_patterns:
            print(f"  Missing: {validation.missing_patterns[:5]}")

        print("\n" + "=" * 50)
        print(f"Output saved to: {output_path}")
        print(f"Release candidate: {release_dir / 'candidate.txt'}")
        print("=" * 50)

        return {
            'success': True,
            'input_size': input_size,
            'output_size': output_size,
            'compression_ratio': input_size / output_size,
            'output_path': str(output_path),
            'validation': validation.is_valid
        }


def run_pipeline(config_path: str = None):
    """Entry point for lossless pipeline."""
    if config_path is None:
        config_path = Path(__file__).parents[2] / "config" / "config.yaml"
    else:
        config_path = Path(config_path)

    pipeline = LosslessPipeline(config_path)
    return pipeline.run()


if __name__ == "__main__":
    import sys
    config = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(config)
