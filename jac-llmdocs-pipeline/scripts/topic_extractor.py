"""
Efficient topic-based documentation extractor.

Makes ONE LLM call per file to extract ALL topics at once.
Outputs ONE file per topic (not a directory).
"""

import re
import yaml
import threading
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from condenser import LLMCondenser


class TopicExtractor:
    """Extracts documentation content organized by topic (efficient version)."""

    def __init__(self, condenser: LLMCondenser, config: Dict):
        self.condenser = condenser
        self.config = config

        # Load topics configuration
        topics_path = Path(__file__).parent.parent / "config" / "topics.yaml"
        with open(topics_path, 'r') as f:
            self.topics_config = yaml.safe_load(f)['topics']

        # Load multi-topic extraction prompt
        prompt_path = Path(__file__).parent.parent / "config" / "multi_topic_extraction_prompt.txt"
        with open(prompt_path, 'r') as f:
            self.extraction_prompt = f.read()

        # Create output directory
        self.output_dir = Path(config.get('extraction', {}).get('output_dir', 'output/1_extracted'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize topic output files (one file per topic)
        self.topic_files = {}
        self.topic_locks = {}  # Locks for thread-safe writing
        for topic_id in self.topics_config:
            topic_file = self.output_dir / f"{topic_id}.md"
            self.topic_files[topic_id] = topic_file
            self.topic_locks[topic_id] = threading.Lock()

    def initialize_files(self):
        """Initialize/clear topic output files with headers."""
        for topic_id, topic_file in self.topic_files.items():
            # Clear existing file
            with open(topic_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self.topics_config[topic_id].get('name', topic_id)}\n\n")

    def determine_relevant_topics(self, file_path: Path, content: str) -> List[str]:
        """
        Determine which topics might be relevant for a file based on keywords.
        Returns list of topic IDs.
        """
        content_lower = content.lower()
        relevant_topics = []

        for topic_id, topic_config in self.topics_config.items():
            keywords = topic_config.get('keywords', [])
            # Check if any keyword appears in content
            if any(keyword.lower() in content_lower for keyword in keywords):
                relevant_topics.append(topic_id)

        # Limit to top topics if too many
        if len(relevant_topics) > 15:
            # Just take first 15 to avoid huge prompts
            relevant_topics = relevant_topics[:15]

        return relevant_topics if relevant_topics else []

    def sanitize_content(self, content: str) -> str:
        """Remove emojis and clean up formatting."""
        # Comprehensive emoji removal
        emoji_pattern = re.compile(
            "["
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F680-\U0001F6FF"  # transport
            "\U0001F700-\U0001F77F"  # alchemical
            "\U0001F780-\U0001F7FF"  # geometric
            "\U0001F800-\U0001F8FF"  # arrows
            "\U0001F900-\U0001F9FF"  # supplemental
            "\U0001FA00-\U0001FA6F"  # chess
            "\U0001FA70-\U0001FAFF"  # extended
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "\u2640-\u2642"
            "\u2600-\u2B55"
            "\u23cf\u23e9-\u23fa"
            "\u25aa-\u25ab\u25b6\u25c0"
            "\u260e\u2611\u2614-\u2615"
            "\u2648-\u2653\u267f\u2693"
            "\u26a1\u26aa-\u26ab"
            "\u26bd-\u26be\u26c4-\u26c5"
            "\u26ce\u26d4\u26ea"
            "\u26f2-\u26f3\u26f5\u26fa\u26fd"
            "\u2705\u270a-\u270b\u2728"
            "\u274c\u274e\u2753-\u2755\u2757"
            "\u2795-\u2797\u27b0\u27bf"
            "\u2b1b-\u2b1c\u2b50\u2b55"
            "\u200d\ufe0f\u3030"
            "]+",
            flags=re.UNICODE
        )
        content = emoji_pattern.sub(' ', content)
        content = content.replace('\ufe0f', '').replace('\u200d', '')
        content = re.sub(r'[\U00010000-\U0010ffff]+', ' ', content)
        content = re.sub(r'[\u2500-\u259F]+', '', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', content)

        lines = content.split('\n')
        lines = [line.strip() for line in lines]
        content = '\n'.join(lines)

        content = re.sub(r'\n-\s*\n', '\n', content)
        content = re.sub(r'\n\*\s*\n', '\n', content)

        return content.strip()

    def is_valid_extraction(self, content: str) -> bool:
        """Check if extracted content is valid."""
        if not content or not content.strip():
            return False

        content_lower = content.lower().strip()

        if content_lower == "no_relevant_content":
            return False

        if "i am sorry" in content_lower or "i apologize" in content_lower or "i cannot extract" in content_lower:
            return False

        if len(content.strip()) < 50:
            return False

        return True

    def extract_all_topics_from_file(self, content: str, relevant_topics: List[str]) -> Dict[str, str]:
        """
        Extract content for ALL topics in a SINGLE LLM call.

        Args:
            content: File content
            relevant_topics: List of topic IDs to extract

        Returns:
            Dict mapping topic_id -> extracted_content
        """
        # Build topics list for prompt
        topic_names = [
            f"{topic_id} ({self.topics_config.get(topic_id, {}).get('name', topic_id)})"
            for topic_id in relevant_topics
        ]
        topics_str = "\n".join([f"- {name}" for name in topic_names])

        # Create prompt
        prompt = self.extraction_prompt.replace("{topics}", topics_str).replace("{content}", content)

        # Call LLM ONCE
        extracted = self.condenser.condense_text(content, prompt)

        # Parse structured output
        topic_contents = {}
        current_topic = None
        current_content = []

        for line in extracted.split('\n'):
            # Check for topic separator
            topic_match = re.match(r'===TOPIC:\s*(.+)===', line.strip())
            if topic_match:
                # Save previous topic
                if current_topic:
                    content_str = '\n'.join(current_content).strip()
                    topic_contents[current_topic] = self.sanitize_content(content_str)

                # Start new topic
                current_topic = topic_match.group(1).strip()
                # Extract topic_id from "topic_id (Topic Name)" format
                if '(' in current_topic:
                    current_topic = current_topic.split('(')[0].strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last topic
        if current_topic:
            content_str = '\n'.join(current_content).strip()
            topic_contents[current_topic] = self.sanitize_content(content_str)

        return topic_contents

    def process_file(self, file_path: Path, source_dir: Path) -> Dict:
        """
        Process a single file, extracting ALL topics in ONE LLM call.
        """
        try:
            # Read source file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return {'success': False, 'file': str(file_path), 'error': 'Empty file'}

            # Determine relevant topics
            relevant_topics = self.determine_relevant_topics(file_path, content)

            if not relevant_topics:
                return {
                    'success': True,
                    'file': str(file_path),
                    'topics_extracted': 0,
                    'message': 'No relevant topics found'
                }

            # Extract ALL topics in ONE call
            topic_contents = self.extract_all_topics_from_file(content, relevant_topics)

            # Append to topic files
            valid_extractions = 0
            for topic_id, topic_content in topic_contents.items():
                if self.is_valid_extraction(topic_content):
                    # Append to single topic file
                    topic_file = self.topic_files.get(topic_id)
                    if topic_file:
                        with self.topic_locks[topic_id]:  # Thread-safe write
                            with open(topic_file, 'a', encoding='utf-8') as f:
                                f.write(f"\n## From: {file_path.name}\n\n")
                                f.write(topic_content)
                                f.write("\n\n")
                        valid_extractions += 1

            return {
                'success': True,
                'file': str(file_path),
                'topics_found': len(relevant_topics),
                'topics_extracted': valid_extractions,
                'llm_calls': 1  # Only 1 call per file!
            }

        except Exception as e:
            return {
                'success': False,
                'file': str(file_path),
                'error': str(e)
            }

    def extract_all(self, source_dir: Path, skip_patterns: List[str] = None) -> Dict:
        """Extract topics from all files."""
        self.initialize_files()
        
        skip_patterns = skip_patterns or []

        # Find all markdown files
        md_files = []
        for pattern in ['**/*.md', '**/*.markdown']:
            md_files.extend(source_dir.glob(pattern))

        # Filter out skipped files
        md_files = [
            f for f in md_files
            if not any(f.match(pattern) for pattern in skip_patterns)
        ]

        print(f"\nStage 1: Efficient Topic Extraction")
        print(f"Source: {source_dir}")
        print(f"Output: {self.output_dir}")
        print(f"Files to process: {len(md_files)}")
        print(f"Topics: {len(self.topics_config)}")
        print(f"Strategy: ONE LLM call per file (not per topic!)")

        # Process files in parallel
        parallel = self.config.get('processing', {}).get('parallel', True)
        max_workers = self.config.get('processing', {}).get('max_workers', 16)

        results = []
        errors = []
        total_llm_calls = 0

        if parallel and len(md_files) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.process_file, f, source_dir): f
                    for f in md_files
                }

                with tqdm(total=len(md_files), desc="Extracting topics") as pbar:
                    for future in as_completed(futures):
                        result = future.result()
                        if result['success']:
                            results.append(result)
                            total_llm_calls += result.get('llm_calls', 0)
                            if result.get('topics_extracted', 0) > 0:
                                tqdm.write(
                                    f"  {Path(result['file']).name}: "
                                    f"{result['topics_extracted']}/{result['topics_found']} topics extracted"
                                )
                        else:
                            errors.append(result)
                            tqdm.write(f"  ERROR {Path(result['file']).name}: {result.get('error', 'Unknown')}")
                        pbar.update(1)
        else:
            # Sequential processing
            for file_path in tqdm(md_files, desc="Extracting topics"):
                result = self.process_file(file_path, source_dir)
                if result['success']:
                    results.append(result)
                    total_llm_calls += result.get('llm_calls', 0)
                else:
                    errors.append(result)

        # Print summary
        total_extracted = sum(r.get('topics_extracted', 0) for r in results)

        print(f"\nExtraction complete:")
        print(f"  Files processed: {len(results)}")
        print(f"  Files failed: {len(errors)}")
        print(f"  Total LLM calls: {total_llm_calls} (was {len(md_files) * 10}+ in old version!)")
        print(f"  Total extractions: {total_extracted}")
        print(f"  Output: ONE file per topic in {self.output_dir}")

        return {
            'success': True,
            'files_processed': len(results),
            'files_failed': len(errors),
            'total_extractions': total_extracted,
            'total_llm_calls': total_llm_calls,
            'errors': errors
        }
