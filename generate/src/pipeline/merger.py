import os
import math
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from condenser import LLMCondenser, CondensationResult


@dataclass
class MergeGroup:
    """Group of files to merge together"""
    files: List[Path]
    output_name: str
    stage: int


class DocumentMerger:
    def __init__(self, condenser: LLMCondenser, config: Dict = None):
        self.condenser = condenser
        self.config = config or {}

        # Load merge prompt from config
        prompt_path = self.config.get('prompts', {}).get('merge', 'config/merge_prompt.txt')
        prompt_file = Path(__file__).parent.parent / prompt_path
        with open(prompt_file, 'r') as f:
            self.merge_prompt_template = f.read()

    def calculate_stages(self, total_files: int, merge_ratio: int) -> List[int]:
        """
        Calculate number of files at each stage.

        Example with 88 files and 4:1 ratio:
        Stage 1: 88 files
        Stage 2: 22 files (88/4)
        Stage 3: 6 files (22/4, rounded up)
        Stage 4: 2 files (6/4, rounded up)
        Stage 5: 1 file (2/4, rounded up)
        """
        stages = [total_files]
        current = total_files

        while current > 1:
            current = math.ceil(current / merge_ratio)
            stages.append(current)

        return stages

    def group_files_for_stage(
        self,
        input_files: List[Path],
        target_groups: int,
        stage_num: int
    ) -> List[MergeGroup]:
        """
        Evenly distribute files into groups.

        Args:
            input_files: Files to group
            target_groups: Number of groups to create
            stage_num: Current stage number

        Returns:
            List of MergeGroup objects
        """
        files_per_group = math.ceil(len(input_files) / target_groups)
        groups = []

        for i in range(target_groups):
            start_idx = i * files_per_group
            end_idx = min(start_idx + files_per_group, len(input_files))

            if start_idx >= len(input_files):
                break

            group_files = input_files[start_idx:end_idx]
            output_name = f"stage{stage_num}_group{i+1:03d}.txt"

            groups.append(MergeGroup(
                files=group_files,
                output_name=output_name,
                stage=stage_num
            ))

        return groups

    def merge_files(self, files: List[Path]) -> str:
        """
        Merge multiple files into one string.

        Includes file metadata and separators for context.
        """
        merged_content = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content:
                    # Add file metadata
                    relative_path = file_path.name
                    merged_content.append(f"[Source: {relative_path}]")
                    merged_content.append(content)
                    merged_content.append("")  # Separator

            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")
                continue

        return "\n".join(merged_content)

    def condense_merged_content(
        self,
        content: str,
        group_name: str,
        preserve_structure: bool = True
    ) -> CondensationResult:
        """
        Condense merged content using merge-specific prompt.

        Uses the merge prompt template which focuses on eliminating redundancy
        and consolidating information from multiple sources.
        """
        import time

        start_time = time.time()

        try:
            # Use merge prompt instead of condensation prompt
            merge_prompt = self.merge_prompt_template.replace('{content}', content)

            # Call OpenRouter directly with merge prompt
            condensed = self.condenser.condense_with_openrouter(content, merge_prompt)

            original_tokens = self.condenser.estimate_tokens(content)
            condensed_tokens = self.condenser.estimate_tokens(condensed)
            compression_ratio = 1 - (condensed_tokens / original_tokens) if original_tokens > 0 else 0
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
            processing_time = time.time() - start_time
            return CondensationResult(
                original_content=content,
                condensed_content="",
                original_tokens=0,
                condensed_tokens=0,
                compression_ratio=0,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )

    def process_group(
        self,
        group: MergeGroup,
        output_dir: Path,
        stage_num: int,
        group_num: int,
        preserve_structure: bool = True
    ) -> Dict:
        """Process a single merge group"""
        try:
            # Merge files
            merged_content = self.merge_files(group.files)

            if not merged_content.strip():
                return {
                    'success': False,
                    'group_num': group_num,
                    'error': 'Empty merged content'
                }

            # Condense merged content
            result = self.condense_merged_content(
                merged_content,
                f"Stage {stage_num} Group {group_num}",
                preserve_structure=preserve_structure
            )

            if result.success:
                output_path = output_dir / group.output_name
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.condensed_content)

                return {
                    'success': True,
                    'group_num': group_num,
                    'output_path': output_path,
                    'original_tokens': result.original_tokens,
                    'condensed_tokens': result.condensed_tokens,
                    'compression_ratio': result.compression_ratio,
                    'num_files': len(group.files)
                }
            else:
                return {
                    'success': False,
                    'group_num': group_num,
                    'error': result.error
                }

        except Exception as e:
            return {
                'success': False,
                'group_num': group_num,
                'error': str(e)
            }

    def process_stage(
        self,
        input_dir: Path,
        output_dir: Path,
        stage_num: int,
        merge_ratio: int,
        preserve_structure: bool = True,
        max_workers: int = 8
    ) -> List[Path]:
        """
        Process one merge stage with concurrent group processing.

        Returns:
            List of output file paths for next stage
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get all input files
        input_files = sorted(list(input_dir.glob("*.txt")) + list(input_dir.glob("*.md")))

        if not input_files:
            # Check subdirectories
            input_files = sorted(list(input_dir.rglob("*.txt")) + list(input_dir.rglob("*.md")))

        if not input_files:
            raise ValueError(f"No files found in {input_dir}")

        # Calculate target number of groups
        target_groups = math.ceil(len(input_files) / merge_ratio)

        print(f"\nStage {stage_num}: {len(input_files)} files → {target_groups} groups (parallel workers: {max_workers})")

        # Group files
        groups = self.group_files_for_stage(input_files, target_groups, stage_num)

        output_files = []

        # Process groups in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_group = {
                executor.submit(
                    self.process_group,
                    group,
                    output_dir,
                    stage_num,
                    i,
                    preserve_structure
                ): (i, group)
                for i, group in enumerate(groups, 1)
            }

            pbar = tqdm(as_completed(future_to_group), total=len(groups), desc=f"Stage {stage_num}")
            for future in pbar:
                group_num, group = future_to_group[future]
                try:
                    result = future.result()

                    if result['success']:
                        output_files.append(result['output_path'])
                        tqdm.write(f"  Group {result['group_num']}/{len(groups)}: "
                              f"{result['num_files']} files → "
                              f"{result['original_tokens']:,} → {result['condensed_tokens']:,} tokens "
                              f"({result['compression_ratio']:.1%})")
                    else:
                        tqdm.write(f"  Group {result['group_num']}/{len(groups)}: Failed - {result['error']}")

                except Exception as e:
                    tqdm.write(f"  Group {group_num}/{len(groups)}: Exception - {str(e)}")

        return output_files

    def run_multi_stage_merge(
        self,
        input_dir: Path,
        base_output_dir: Path,
        merge_ratio: int = 4,
        preserve_structure: bool = True,
        max_workers: int = 8
    ) -> Path:
        """
        Run complete multi-stage merge process.

        Args:
            input_dir: Directory with initial condensed docs
            base_output_dir: Base directory for merge outputs
            merge_ratio: Files to merge per group (e.g., 4:1 means 4→1)
            preserve_structure: Whether to preserve document structure

        Returns:
            Path to final merged document
        """
        print("=" * 80)
        print("MULTI-STAGE DOCUMENT MERGE")
        print("=" * 80)

        # Get initial file count
        initial_files = list(input_dir.rglob("*.txt")) + list(input_dir.rglob("*.md"))
        total_files = len(initial_files)

        if total_files == 0:
            raise ValueError(f"No files found in {input_dir}")

        # Calculate stages
        stages = self.calculate_stages(total_files, merge_ratio)

        print(f"\nInitial files: {total_files}")
        print(f"Merge ratio: {merge_ratio}:1")
        print(f"Stages planned: {len(stages) - 1}")
        for i, count in enumerate(stages):
            if i == 0:
                print(f"  Stage {i} (input): {count} files")
            else:
                print(f"  Stage {i}: {count} files")

        print("\n" + "-" * 80)

        # Process each stage
        current_input = input_dir
        stage_outputs = []

        for stage_num in range(1, len(stages)):
            stage_output_dir = base_output_dir / f"stage_{stage_num}"

            output_files = self.process_stage(
                input_dir=current_input,
                output_dir=stage_output_dir,
                stage_num=stage_num,
                merge_ratio=merge_ratio,
                preserve_structure=preserve_structure,
                max_workers=max_workers
            )

            stage_outputs.append(output_files)
            current_input = stage_output_dir

            # If we're down to 1 file, we're done
            if len(output_files) == 1:
                print("\n" + "=" * 80)
                print(f"MERGE COMPLETE: Final document at {output_files[0]}")
                print("=" * 80)
                return output_files[0]

        # Get the last output file
        if stage_outputs and stage_outputs[-1]:
            final_file = stage_outputs[-1][0]
            print("\n" + "=" * 80)
            print(f"MERGE COMPLETE: Final document at {final_file}")
            print("=" * 80)
            return final_file
        else:
            raise ValueError("Merge process failed to produce output")
