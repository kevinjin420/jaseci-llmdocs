#!/usr/bin/env python3
"""
JAC Documentation Pipeline - Topic-Based Architecture

Stage 1: Extract topic-specific content from all documentation files
Stage 2: Merge all files within each topic category
Stage 3: Format and combine all topics into final compact reference
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

from condenser import LLMCondenser
from topic_extractor import TopicExtractor
from topic_merger import TopicMerger
from hierarchical_merger import HierarchicalMerger
from ultra_compressor import UltraCompressor


class TopicBasedPipeline:
    """
    Topic-based documentation pipeline.

    New architecture:
    1. Extract: Parse docs and extract content by topic
    2. Topic Merge: Within each topic, merge all related docs
    3. Hierarchical Merge: Combine all topics into one unified document
    4. Format: Final cleanup and formatting
    """

    def __init__(self, config_path: str):
        """Initialize pipeline with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize LLM condenser
        self.condenser = LLMCondenser(self.config)

        # Initialize pipeline components
        self.extractor = TopicExtractor(self.condenser, self.config)
        self.merger = TopicMerger(self.condenser, self.config)
        self.hierarchical_merger = HierarchicalMerger(self.condenser, self.config)
        self.compressor = UltraCompressor(self.condenser, self.config)

        # Setup directories
        self.source_dir = Path(self.config['source_dir'])
        self.output_dir = Path(self.config.get('ultra_compression', {}).get('output_dir', 'output/4_final'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_stage_1_extraction(self):
        """Stage 1: Extract topic-specific content."""
        print("\n" + "=" * 80)
        print("STAGE 1: TOPIC EXTRACTION")
        print("=" * 80)

        skip_patterns = self.config['processing'].get('skip_patterns', [])
        result = self.extractor.extract_all(self.source_dir, skip_patterns)

        if not result['success']:
            print(f"Stage 1 failed!")
            return False

        print(f"\nStage 1 complete: {result['total_extractions']} extractions from {result['files_processed']} files")
        return True

    def run_stage_2_merge(self):
        """Stage 2: Merge all files within each topic category."""
        print("\n" + "=" * 80)
        print("STAGE 2: TOPIC MERGING")
        print("=" * 80)

        result = self.merger.merge_all_topics()

        if not result['success']:
            print(f"Stage 2 failed!")
            return False

        print(f"\nStage 2 complete: {result['topics_processed']} topics merged")
        return True

    def run_stage_3_hierarchical_merge(self):
        """Stage 3: Hierarchical merge of all topics into one file."""
        print("\n" + "=" * 80)
        print("STAGE 3: HIERARCHICAL MERGE")
        print("=" * 80)
        
        # User defined ratio or default 4
        ratio = self.config.get('hierarchical_merge', {}).get('ratio', 4)
        result = self.hierarchical_merger.run_merge(merge_ratio=ratio)
        
        if not result['success']:
            print(f"Stage 3 failed: {result.get('error')}")
            return False
            
        print(f"\nStage 3 complete. Output: {result['output_path']}")
        return True

    def run_stage_4_format(self):
        """Stage 4: Final formatting and cleanup."""
        print("\n" + "=" * 80)
        print("STAGE 4: FINAL FORMATTING")
        print("=" * 80)

        # Input comes from Stage 3 output
        input_file = Path(self.config.get('hierarchical_merge', {}).get('output_dir', 'output/3_hierarchical')) / "unified_doc.txt"
        
        if not input_file.exists():
            print(f"Error: Input file for Stage 4 not found: {input_file}")
            return False
            
        final_output = self.config.get('ultra_compression', {}).get('output_file', 'jac_docs_final.txt')
        output_path = self.output_dir / final_output

        # We use format_file instead of combine_and_format_topics since it's already combined
        result = self.compressor.format_file(input_file, output_path)

        if not result.success:
            print(f"Stage 4 failed: {result.error}")
            return False

        print(f"\nStage 4 complete:")
        print(f"  Original: {result.original_tokens:,} tokens")
        print(f"  Final: {result.compressed_tokens:,} tokens")
        print(f"  Reduction: {result.compression_ratio:.1%}")
        print(f"  Output: {output_path}")

        return True

    def run_full_pipeline(self):
        """Run all four stages in sequence."""
        start_time = datetime.now()

        print("\n" + "=" * 80)
        print("JAC DOCUMENTATION PIPELINE")
        print("=" * 80)
        print(f"Source: {self.source_dir}")
        print(f"Output: {self.output_dir}")

        if not self.run_stage_1_extraction(): return False
        if not self.run_stage_2_merge(): return False
        if not self.run_stage_3_hierarchical_merge(): return False
        if not self.run_stage_4_format(): return False

        end_time = datetime.now()
        print(f"\nPipeline Finished: {end_time - start_time}")
        return True


def main():
    """Main entry point."""
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    pipeline = TopicBasedPipeline(str(config_path))

    stage_to_run = None
    if len(sys.argv) > 1:
        try:
            stage_to_run = int(sys.argv[1])
        except ValueError:
            pass

    try:
        if stage_to_run is None:
            pipeline.run_full_pipeline()
        elif stage_to_run == 1:
            pipeline.run_stage_1_extraction()
        elif stage_to_run == 2:
            pipeline.run_stage_2_merge()
        elif stage_to_run == 3:
            pipeline.run_stage_3_hierarchical_merge()
        elif stage_to_run == 4:
            pipeline.run_stage_4_format()
        else:
            print("Invalid stage. Use 1-4.")
            
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
