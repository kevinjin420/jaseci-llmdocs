"""
Topic-based documentation merger.

Merges all files within each topic category into comprehensive topic guides.
"""

import math
import re
import yaml
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from condenser import LLMCondenser


class TopicMerger:
    """Merges documentation files within each topic category."""

    def __init__(self, condenser: LLMCondenser, config: Dict):
        self.condenser = condenser
        self.config = config

        # Load topics configuration
        topics_path = Path(__file__).parent.parent / "config" / "topics.yaml"
        with open(topics_path, 'r') as f:
            self.topics_config = yaml.safe_load(f)['topics']

        # Load merge prompt template
        prompt_path = self.config.get('prompts', {}).get('merge', 'config/merge_prompt.txt')
        prompt_file = Path(__file__).parent.parent / prompt_path
        with open(prompt_file, 'r') as f:
            self.merge_prompt_template = f.read()

        # Setup directories
        self.input_dir = Path(config.get('extraction', {}).get('output_dir', 'output/1_extracted'))
        self.output_dir = Path(config.get('merge', {}).get('output_dir', 'output/2_merged'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def chunk_content(self, content: str, max_chars: int = 12000) -> List[str]:
        """
        Split content into chunks that fit within context window.
        Prioritizes splitting by file markers, then headers, then paragraphs.
        """
        if len(content) <= max_chars:
            return [content]

        chunks = []
        current_chunk = []
        current_len = 0

        # 1. Split by file markers
        parts = re.split(r'(?=\n## From: )', content)
        
        for part in parts:
            if not part.strip():
                continue
                
            part_len = len(part)
            
            # If single part is huge, split by structure
            if part_len > max_chars:
                # Save current accumulator first
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                
                # Level 2: Split by H2 Headers
                subparts = re.split(r'(?=\n## )', part)
                temp_chunk = []
                temp_len = 0
                
                for sub in subparts:
                    if len(sub) > max_chars:
                        # Save temp accumulator
                        if temp_chunk:
                            chunks.append("".join(temp_chunk))
                            temp_chunk = []
                            temp_len = 0
                            
                        # Level 3: Split by H3 Headers
                        subsubparts = re.split(r'(?=\n### )', sub)
                        sub_temp_chunk = []
                        sub_temp_len = 0
                        
                        for subsub in subsubparts:
                            if len(subsub) > max_chars:
                                # Save sub-temp accumulator
                                if sub_temp_chunk:
                                    chunks.append("".join(sub_temp_chunk))
                                    sub_temp_chunk = []
                                    sub_temp_len = 0
                                    
                                # Level 4: Split by Paragraphs
                                paras = subsub.split('\n\n')
                                para_chunk = []
                                para_len = 0
                                
                                for para in paras:
                                    if para_len + len(para) > max_chars:
                                        chunks.append("\n\n".join(para_chunk))
                                        para_chunk = [para]
                                        para_len = len(para)
                                    else:
                                        para_chunk.append(para)
                                        para_len += len(para) + 2
                                        
                                if para_chunk:
                                    chunks.append("\n\n".join(para_chunk))
                            else:
                                if sub_temp_len + len(subsub) > max_chars:
                                    chunks.append("".join(sub_temp_chunk))
                                    sub_temp_chunk = [subsub]
                                    sub_temp_len = len(subsub)
                                else:
                                    sub_temp_chunk.append(subsub)
                                    sub_temp_len += len(subsub)
                                    
                        if sub_temp_chunk:
                            chunks.append("".join(sub_temp_chunk))

                    else:
                        if temp_len + len(sub) > max_chars:
                            chunks.append("".join(temp_chunk))
                            temp_chunk = [sub]
                            temp_len = len(sub)
                        else:
                            temp_chunk.append(sub)
                            temp_len += len(sub)
                            
                if temp_chunk:
                    chunks.append("".join(temp_chunk))
                    
            # If adding part exceeds limit, save current chunk
            elif current_len + part_len > max_chars:
                chunks.append("".join(current_chunk))
                current_chunk = [part]
                current_len = part_len
            else:
                current_chunk.append(part)
                current_len += part_len
                
        if current_chunk:
            chunks.append("".join(current_chunk))
            
        return chunks

    def recursive_merge(self, content: str, topic_name: str) -> str:
        """
        Recursively merge content using a 4:1 strategy until it fits in one block.
        """
        # Check if content is small enough for single pass
        if len(content) < 20000:
            prompt = self.merge_prompt_template.replace("{content}", content)
            prompt_with_context = f"Topic: {topic_name}\n\n{prompt}"
            return self.condenser.condense_text(content, prompt_with_context)

        # Chunk content
        chunks = self.chunk_content(content)
        if len(chunks) == 1:
            prompt = self.merge_prompt_template.replace("{content}", chunks[0])
            prompt_with_context = f"Topic: {topic_name}\n\n{prompt}"
            return self.condenser.condense_text(chunks[0], prompt_with_context)
            
        print(f"  Topic '{topic_name}' too large ({len(content)} chars), splitting into {len(chunks)} chunks...")
        
        # Process chunks in groups of 4
        merge_ratio = 4
        new_chunks = []
        
        # Process groups in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(0, len(chunks), merge_ratio):
                group = chunks[i:i + merge_ratio]
                group_content = "\n\n".join(group)
                
                prompt = self.merge_prompt_template.replace("{content}", group_content)
                prompt_with_context = f"Topic: {topic_name} (Part {i//merge_ratio + 1})\n\n{prompt}"
                
                futures.append(executor.submit(self.condenser.condense_text, group_content, prompt_with_context))
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.strip():
                        new_chunks.append(result)
                except Exception as e:
                    print(f"  Error merging chunk for {topic_name}: {e}")

        if not new_chunks:
            return ""
            
        # Join results and recurse
        merged_content = "\n\n".join(new_chunks)
        return self.recursive_merge(merged_content, topic_name)

    def process_topic(self, topic_id: str) -> Dict:
        """
        Process a single topic file (Stage 1 now outputs ONE file per topic).

        Args:
            topic_id: Topic identifier

        Returns:
            Dict with processing results
        """
        # Stage 1 now outputs ONE file per topic, not a directory
        topic_file = self.input_dir / f"{topic_id}.md"

        if not topic_file.exists():
            return {
                'success': False,
                'topic': topic_id,
                'error': f'Topic file does not exist: {topic_file}'
            }

        # Read single topic file
        try:
            with open(topic_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
        except Exception as e:
            return {
                'success': False,
                'topic': topic_id,
                'error': f'Failed to read topic file: {e}'
            }

        if not content:
            return {
                'success': False,
                'topic': topic_id,
                'error': 'Topic file is empty'
            }

        try:
            topic_name = self.topics_config.get(topic_id, {}).get('name', topic_id)

            # Apply Recursive LLM merge
            merged_content = self.recursive_merge(content, topic_name)

            if not merged_content.strip():
                return {
                    'success': False,
                    'topic': topic_id,
                    'error': 'Merged content is empty'
                }

            # Write output
            output_path = self.output_dir / f"{topic_id}.txt"

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {topic_name}\n\n")
                f.write(merged_content)

            # Calculate statistics
            original_size = len(content)
            merged_size = len(merged_content)

            return {
                'success': True,
                'topic': topic_id,
                'topic_name': topic_name,
                'original_size': original_size,
                'merged_size': merged_size,
                'compression_ratio': merged_size / original_size if original_size > 0 else 0,
                'output_path': str(output_path)
            }

        except Exception as e:
            return {
                'success': False,
                'topic': topic_id,
                'error': str(e)
            }

    def merge_all_topics(self) -> Dict:
        """
        Merge files for all topics in parallel.

        Returns:
            Dict with merge statistics
        """
        print(f"\nStage 2: Topic Merging")
        print(f"Input: {self.input_dir}")
        print(f"Output: {self.output_dir}")

        # Find all topic files (Stage 1 outputs ONE file per topic)
        topic_ids = []
        for topic_id in self.topics_config.keys():
            topic_file = self.input_dir / f"{topic_id}.md"
            if topic_file.exists() and topic_file.stat().st_size > 0:
                topic_ids.append(topic_id)

        if not topic_ids:
            print("No topics to merge!")
            return {'success': False, 'error': 'No topics found'}

        print(f"Topics to merge: {len(topic_ids)}")

        # Process topics in parallel
        parallel = self.config.get('processing', {}).get('parallel', True)
        max_workers = self.config.get('merge', {}).get('max_workers', 16)

        results = []
        errors = []

        if parallel and len(topic_ids) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.process_topic, topic_id): topic_id
                    for topic_id in topic_ids
                }

                with tqdm(total=len(topic_ids), desc="Merging topics") as pbar:
                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            results.append(result)
                            tqdm.write(
                                f"  {result['topic_name']:30s}: "
                                f"{result['original_size']:,} → {result['merged_size']:,} chars "
                                f"({result['compression_ratio']:.1%})"
                            )
                        else:
                            errors.append(result)
                            tqdm.write(f"  ERROR {result['topic']}: {result.get('error', 'Unknown')}")
                        pbar.update(1)
        else:
            # Sequential processing
            for topic_id in tqdm(topic_ids, desc="Merging topics"):
                result = self.process_topic(topic_id)
                if result['success']:
                    results.append(result)
                else:
                    errors.append(result)

        # Calculate overall statistics
        total_original = sum(r['original_size'] for r in results)
        total_merged = sum(r['merged_size'] for r in results)
        overall_compression = total_merged / total_original if total_original > 0 else 0

        # Print summary
        print(f"\nMerge complete:")
        print(f"  Topics processed: {len(results)}")
        print(f"  Topics failed: {len(errors)}")
        print(f"  Total size: {total_original:,} → {total_merged:,} chars ({overall_compression:.1%})")

        return {
            'success': True,
            'topics_processed': len(results),
            'topics_failed': len(errors),
            'total_files': len(topic_ids),
            'total_original_size': total_original,
            'total_merged_size': total_merged,
            'compression_ratio': overall_compression,
            'results': results,
            'errors': errors
        }
