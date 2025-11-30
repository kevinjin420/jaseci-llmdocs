#!/usr/bin/env python3

import os
import sys
import json
import yaml
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from parser import DocumentParser, DocFile, DocSection
from condenser import LLMCondenser, CondensationResult
from merger import DocumentMerger
from ultra_compressor import UltraCompressor


class CondensationPipeline:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.parser = DocumentParser(
            source_dir=self.config['source_dir'],
            skip_patterns=self.config['processing'].get('skip_patterns', [])
        )

        self.condenser = LLMCondenser(self.config)

        self.output_dir = Path(self.config['output_dir'])
        self.metrics_dir = Path(self.config['metrics_dir'])

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.results = []
        self.errors = []

    def process_section(self, section: DocSection, file_rel_path: str) -> Dict:
        result = self.condenser.condense(section.content, section.section_title)

        return {
            'file': file_rel_path,
            'section': section.section_title,
            'start_line': section.start_line,
            'end_line': section.end_line,
            'level': section.level,
            'result': result
        }

    def process_file(self, doc_file: DocFile, parallel_sections: bool = False, section_workers: int = 4) -> List[Dict]:
        sections_to_process = [s for s in doc_file.sections if len(s.content.strip()) >= 50]

        if not sections_to_process:
            return []

        if parallel_sections and len(sections_to_process) > 1:
            # Process sections in parallel within this file
            results = []
            with ThreadPoolExecutor(max_workers=section_workers) as executor:
                future_to_section = {
                    executor.submit(self.process_section, section, doc_file.relative_path): section
                    for section in sections_to_process
                }

                for future in as_completed(future_to_section):
                    section = future_to_section[future]
                    try:
                        result_dict = future.result()
                        results.append(result_dict)

                        if not result_dict['result'].success:
                            self.errors.append({
                                'file': doc_file.relative_path,
                                'section': section.section_title,
                                'error': result_dict['result'].error
                            })

                    except Exception as e:
                        self.errors.append({
                            'file': doc_file.relative_path,
                            'section': section.section_title,
                            'error': str(e)
                        })
            return results
        else:
            # Process sections sequentially
            results = []
            for section in sections_to_process:
                try:
                    result_dict = self.process_section(section, doc_file.relative_path)
                    results.append(result_dict)

                    if not result_dict['result'].success:
                        self.errors.append({
                            'file': doc_file.relative_path,
                            'section': section.section_title,
                            'error': result_dict['result'].error
                        })

                except Exception as e:
                    self.errors.append({
                        'file': doc_file.relative_path,
                        'section': section.section_title,
                        'error': str(e)
                    })

            return results

    def save_condensed_file(self, doc_file: DocFile, section_results: List[Dict]):
        output_path = self.output_dir / doc_file.relative_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        condensed_sections = []
        for result_dict in section_results:
            if result_dict['result'].success:
                formatted = self.condenser.format_output(
                    result_dict['result'].condensed_content,
                    result_dict['section']
                )
                condensed_sections.append(formatted)

        if condensed_sections:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(condensed_sections))

    def run(self, parallel: bool = True, max_workers: int = 4, parallel_sections: bool = False, section_workers: int = 4):
        print("=" * 80)
        print("JAC LLM DOCUMENTATION CONDENSATION PIPELINE")
        print("=" * 80)
        print(f"Config: {max_workers} file workers, {section_workers} section workers per file")
        print(f"Parallel files: {parallel}, Parallel sections: {parallel_sections}")

        categories = self.config['processing'].get('categories')
        doc_files = self.parser.parse_all(categories=categories)

        stats = self.parser.get_statistics(doc_files)
        print(f"\nParsed {stats['total_files']} files:")
        print(f"  - {stats['total_sections']} sections")
        print(f"  - {stats['total_lines']:,} lines")
        print(f"  - ~{stats['estimated_tokens']:,} tokens")
        print(f"\nCategories: {stats['categories']}")
        print("\n" + "-" * 80)

        start_time = datetime.now()

        if parallel and len(doc_files) > 1:
            print(f"\nProcessing files in parallel (workers={max_workers})...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self.process_file, doc_file, parallel_sections, section_workers): doc_file
                    for doc_file in doc_files
                }

                for future in tqdm(as_completed(future_to_file), total=len(doc_files)):
                    doc_file = future_to_file[future]
                    try:
                        section_results = future.result()
                        self.results.extend(section_results)
                        self.save_condensed_file(doc_file, section_results)
                    except Exception as e:
                        self.errors.append({
                            'file': doc_file.relative_path,
                            'error': str(e)
                        })
        else:
            print(f"\nProcessing files sequentially...")
            for doc_file in tqdm(doc_files):
                try:
                    section_results = self.process_file(doc_file, parallel_sections, section_workers)
                    self.results.extend(section_results)
                    self.save_condensed_file(doc_file, section_results)
                except Exception as e:
                    self.errors.append({
                        'file': doc_file.relative_path,
                        'error': str(e)
                    })

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        report = self.generate_report(stats, processing_time)

        return report

    def generate_report(self, input_stats: Dict, processing_time: float):
        successful_results = [r for r in self.results if r['result'].success]

        total_original_tokens = sum(r['result'].original_tokens for r in successful_results)
        total_condensed_tokens = sum(r['result'].condensed_tokens for r in successful_results)

        overall_ratio = total_condensed_tokens / total_original_tokens if total_original_tokens > 0 else 0

        report = {
            'timestamp': datetime.now().isoformat(),
            'input': input_stats,
            'processing': {
                'total_sections_processed': len(self.results),
                'successful': len(successful_results),
                'failed': len(self.errors),
                'processing_time_seconds': processing_time
            },
            'compression': {
                'original_tokens': total_original_tokens,
                'condensed_tokens': total_condensed_tokens,
                'compression_ratio': overall_ratio,
                'token_reduction': total_original_tokens - total_condensed_tokens,
                'reduction_percentage': (1 - overall_ratio) * 100
            },
            'errors': self.errors
        }

        print("\n" + "=" * 80)
        print("CONDENSATION REPORT")
        print("=" * 80)
        print(f"\nProcessing completed in {processing_time:.2f}s")
        print(f"\nSections processed: {len(successful_results)} / {len(self.results)}")
        print(f"Errors: {len(self.errors)}")
        print(f"\nCompression Results:")
        print(f"  Original tokens:  ~{total_original_tokens:,}")
        print(f"  Condensed tokens: ~{total_condensed_tokens:,}")
        print(f"  Compression ratio: {overall_ratio:.2%}")
        print(f"  Token reduction:   ~{total_original_tokens - total_condensed_tokens:,} ({(1-overall_ratio)*100:.1f}%)")
        print(f"\nOutput directory: {self.output_dir}")

        if self.errors:
            print(f"\nErrors encountered:")
            for error in self.errors[:5]:
                print(f"  - {error['file']}: {error.get('error', 'Unknown error')}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        return report


def run_merge_stage(config: Dict, condenser: LLMCondenser) -> Path:
    """Run multi-stage merge on condensed output"""
    merge_config = config.get('merge', {})

    if not merge_config.get('enabled', False):
        print("\nMerge stage disabled in config (merge.enabled: false)")
        return None

    print("\n" + "=" * 80)
    print("STARTING MERGE STAGE")
    print("=" * 80)

    input_dir = Path(config['output_dir'])
    base_output_dir = Path(merge_config.get('output_dir', './output/merged'))
    merge_ratio = merge_config.get('ratio', 4)
    max_workers = merge_config.get('max_workers', 8)

    print(f"Merge workers: {max_workers} (concurrent group processing per stage)")

    merger = DocumentMerger(condenser, config)

    start_time = datetime.now()

    try:
        final_file = merger.run_multi_stage_merge(
            input_dir=input_dir,
            base_output_dir=base_output_dir,
            merge_ratio=merge_ratio,
            preserve_structure=merge_config.get('preserve_structure', True),
            max_workers=max_workers
        )

        # Copy to final output name
        final_output_name = merge_config.get('final_output', 'jac_documentation_final.txt')
        final_output_path = base_output_dir / final_output_name

        if final_file != final_output_path:
            shutil.copy(final_file, final_output_path)
            print(f"\nFinal document saved as: {final_output_path}")

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Get final stats
        with open(final_output_path, 'r', encoding='utf-8') as f:
            final_content = f.read()
            final_chars = len(final_content)
            final_tokens = final_chars // 4

        # Generate merge report
        merge_report = {
            'timestamp': datetime.now().isoformat(),
            'input_dir': str(input_dir),
            'output_dir': str(base_output_dir),
            'merge_ratio': merge_ratio,
            'processing_time_seconds': processing_time,
            'final_file': str(final_output_path),
            'final_stats': {
                'chars': final_chars,
                'estimated_tokens': final_tokens
            }
        }

        print(f"\nFinal document stats:")
        print(f"  Characters: {final_chars:,}")
        print(f"  Estimated tokens: ~{final_tokens:,}")
        print(f"  Processing time: {processing_time:.2f}s")

        return final_output_path

    except Exception as e:
        print(f"\nError during merge: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_ultra_compression_stage(config: Dict, condenser: LLMCondenser, merged_doc_path: Path) -> Path:
    """Run ultra-compression stage to create reference-format documentation"""
    ultra_config = config.get('ultra_compression', {})

    if not ultra_config.get('enabled', False):
        print("\nUltra-compression stage disabled in config (ultra_compression.enabled: false)")
        return merged_doc_path

    print("\n" + "=" * 80)
    print("STARTING ULTRA-COMPRESSION STAGE")
    print("=" * 80)

    output_dir = Path(ultra_config.get('output_dir', './output/3_ultra'))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = ultra_config.get('output_file', 'jac_docs_ultra.txt')
    output_path = output_dir / output_file

    passes = ultra_config.get('passes', 2)

    print(f"Ultra-compression passes: {passes}")

    start_time = datetime.now()

    try:
        # Initialize ultra-compressor with config
        compressor = UltraCompressor(condenser, config)

        # Read merged document
        with open(merged_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Compress with multiple passes
        result = compressor.multi_pass_compress(
            content,
            passes=passes,
            name=merged_doc_path.name
        )

        if result.success:
            # Write output
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.content)

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # Generate ultra-compression report
            ultra_report = {
                'timestamp': datetime.now().isoformat(),
                'input_file': str(merged_doc_path),
                'output_file': str(output_path),
                'passes': passes,
                'processing_time_seconds': processing_time,
                'original_tokens': result.original_tokens,
                'compressed_tokens': result.compressed_tokens,
                'compression_ratio': result.compression_ratio
            }

            print(f"\nUltra-compressed document stats:")
            print(f"  Original tokens: {result.original_tokens:,}")
            print(f"  Compressed tokens: {result.compressed_tokens:,}")
            print(f"  Compression ratio: {result.compression_ratio:.1%}")
            print(f"  Processing time: {processing_time:.2f}s")

            return output_path
        else:
            print(f"\nError during ultra-compression: {result.error}")
            return merged_doc_path

    except Exception as e:
        print(f"\nError during ultra-compression: {e}")
        import traceback
        traceback.print_exc()
        return merged_doc_path


def main():
    """
    Run the documentation pipeline.

    Usage:
        python pipeline.py       # Run all 3 stages
        python pipeline.py 1     # Run only stage 1 (condensation)
        python pipeline.py 2     # Run only stage 2 (merge)
        python pipeline.py 3     # Run only stage 3 (ultra-compression)
    """
    # Parse stage argument
    stage_to_run = None
    if len(sys.argv) > 1:
        try:
            stage_to_run = int(sys.argv[1])
            if stage_to_run not in [1, 2, 3]:
                print(f"Error: Stage must be 1, 2, or 3 (got {stage_to_run})")
                print("Usage: python pipeline.py [stage]")
                print("  stage: 1=condensation, 2=merge, 3=ultra-compression (optional, default=all)")
                return
        except ValueError:
            print(f"Error: Invalid stage argument '{sys.argv[1]}' (must be integer 1-3)")
            print("Usage: python pipeline.py [stage]")
            return

    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return

    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Get processing settings from config
    parallel = config['processing'].get('parallel', True)
    max_workers = config['processing'].get('max_workers', 16)
    parallel_sections = config['processing'].get('parallel_sections', True)
    section_workers = config['processing'].get('section_workers', 8)

    # Stage 1: Condensation
    if stage_to_run is None or stage_to_run == 1:
        print("=" * 80)
        print("STAGE 1: CONDENSATION")
        print("=" * 80)

        pipeline = CondensationPipeline(str(config_path))
        condensation_report = pipeline.run(
            parallel=parallel,
            max_workers=max_workers,
            parallel_sections=parallel_sections,
            section_workers=section_workers
        )

        if stage_to_run == 1:
            print("\n" + "=" * 80)
            print("STAGE 1 COMPLETE")
            print("=" * 80)
            print(f"\nCondensed docs: {config['output_dir']}")
            return
    else:
        # Create pipeline for stages 2 and 3
        pipeline = CondensationPipeline(str(config_path))

    # Stage 2: Merge
    if stage_to_run is None or stage_to_run == 2:
        # Check if condensed output exists
        if stage_to_run == 2:
            output_dir = Path(config['output_dir'])
            if not output_dir.exists() or not list(output_dir.rglob("*.txt")):
                print(f"Error: No condensed output found in {output_dir}")
                print("Run stage 1 first: python pipeline.py 1")
                return

        merged_doc = run_merge_stage(config, pipeline.condenser)

        if not merged_doc:
            print("\nMerge stage failed")
            return

        if stage_to_run == 2:
            print("\n" + "=" * 80)
            print("STAGE 2 COMPLETE")
            print("=" * 80)
            print(f"\nMerged document: {merged_doc}")
            return
    else:
        # Find merged doc for stage 3
        merge_config = config.get('merge', {})
        base_output_dir = Path(merge_config.get('output_dir', './output/merged'))
        final_output_name = merge_config.get('final_output', 'jac_documentation_final.txt')
        merged_doc = base_output_dir / final_output_name

        if not merged_doc.exists():
            print(f"Error: Merged document not found: {merged_doc}")
            print("Run stage 2 first: python pipeline.py 2")
            return

    # Stage 3: Ultra-compression
    if stage_to_run is None or stage_to_run == 3:
        final_doc = run_ultra_compression_stage(config, pipeline.condenser, merged_doc)

        if stage_to_run == 3:
            print("\n" + "=" * 80)
            print("STAGE 3 COMPLETE")
            print("=" * 80)
            print(f"\nUltra-compressed reference doc: {final_doc}")
            return

    # All stages complete
    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE")
    print("=" * 80)
    print(f"\nMerged document: {merged_doc}")
    print(f"Ultra-compressed reference doc: {final_doc}")


if __name__ == '__main__':
    main()
