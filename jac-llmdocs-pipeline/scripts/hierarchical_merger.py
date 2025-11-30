"""
Hierarchical Document Merger (Stage 3).

Takes a set of topic files and merges them into a single document 
using a hierarchical strategy (e.g., 4 files -> 1 file) to maintain 
coherence and context.
"""

import math
import os
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from condenser import LLMCondenser

class HierarchicalMerger:
    """
    Merges multiple files into a single document through hierarchical stages.
    """

    def __init__(self, condenser: LLMCondenser, config: Dict):
        self.condenser = condenser
        self.config = config
        
        # Load merge prompt template
        prompt_path = self.config.get('prompts', {}).get('merge', 'config/merge_prompt.txt')
        prompt_file = Path(__file__).parent.parent / prompt_path
        with open(prompt_file, 'r') as f:
            self.merge_prompt_template = f.read()
            
        # Setup directories
        self.input_dir = Path(config.get('merge', {}).get('output_dir', 'output/2_merged'))
        self.output_dir = Path(config.get('hierarchical_merge', {}).get('output_dir', 'output/3_hierarchical'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def merge_group(self, files: List[Path], output_path: Path, stage_num: int, group_num: int):
        """
        Merge a group of files into a single condensed file.
        """
        # 1. Read and Combine Content
        combined_content = []
        for f in files:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read().strip()
                if content:
                    combined_content.append(content)
        
        full_text = "\n\n".join(combined_content)
        
        # 2. Condense using LLM
        # We use the merge prompt to ensure the combined text is synthesized, not just concatenated
        prompt = self.merge_prompt_template.replace("{content}", full_text)
        
        # Add context to prompt
        context_prompt = f"Merging Stage {stage_num}, Group {group_num}\nFiles: {[f.name for f in files]}\n\n{prompt}"
        
        try:
            # If text is huge, we might need to just concatenate (fallback) or split-merge again
            # For now, assuming the input topics are condensed enough (from Stage 2)
            condensed_text = self.condenser.condense_text(full_text, context_prompt)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(condensed_text)
                
            return {
                'success': True,
                'original_len': len(full_text),
                'merged_len': len(condensed_text),
                'files_merged': len(files)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def run_merge(self, merge_ratio: int = 4) -> Dict:
        """
        Execute the hierarchical merge process.
        """
        print(f"\nStage 3: Hierarchical Merge (Ratio {merge_ratio}:1)")
        
        current_files = sorted(list(self.input_dir.glob("*.txt")))
        if not current_files:
            return {'success': False, 'error': 'No input files found from Stage 2'}
            
        stage_count = 1
        
        while len(current_files) > 1:
            print(f"\n  Merge Pass {stage_count}: {len(current_files)} files -> {math.ceil(len(current_files)/merge_ratio)} files")
            
            # Create output dir for this pass
            pass_dir = self.output_dir / f"pass_{stage_count}"
            pass_dir.mkdir(parents=True, exist_ok=True)
            
            # Group files
            groups = []
            for i in range(0, len(current_files), merge_ratio):
                groups.append(current_files[i:i + merge_ratio])
                
            next_files = []
            
            # Process groups
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {}
                for i, group in enumerate(groups):
                    output_file = pass_dir / f"part_{i+1:03d}.txt"
                    futures[executor.submit(self.merge_group, group, output_file, stage_count, i+1)] = output_file
                    
                for future in tqdm(as_completed(futures), total=len(groups), desc=f"    Processing groups"):
                    result = future.result()
                    output_file = futures[future]
                    if result['success']:
                        next_files.append(output_file)
                    else:
                        print(f"    Error merging group: {result['error']}")
            
            current_files = sorted(next_files)
            stage_count += 1
            
        # Final Result
        final_result = self.output_dir / "unified_doc.txt"
        if current_files:
            import shutil
            shutil.copy(current_files[0], final_result)
            print(f"\n  Final merged file: {final_result}")
            
            return {
                'success': True,
                'output_path': str(final_result),
                'final_size': final_result.stat().st_size
            }
        else:
            return {'success': False, 'error': 'Merge process failed to produce a final file'}
