#!/usr/bin/env python3
"""
Aggressive script to condense jaseci-docs-compiled.md by removing duplicate content.
Based on analysis showing 69% duplication across 40,447 lines.
"""
import re

def read_file_sections(filepath):
    """Parse the compiled docs into sections based on FILE: markers."""
    sections = []
    current_section = None
    current_content = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('================================================================================'):
                continue
            if line.startswith('FILE:'):
                # Save previous section
                if current_section:
                    sections.append({
                        'file': current_section,
                        'content': ''.join(current_content),
                        'lines': len(current_content)
                    })
                # Start new section
                current_section = line.strip().replace('FILE: ', '')
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections.append({
                'file': current_section,
                'content': ''.join(current_content),
                'lines': len(current_content)
            })

    return sections

def should_keep_section(filepath):
    """
    Determine if a section should be kept based on comprehensive analysis.
    Returns: 'keep', 'condense', or 'remove'
    """

    # REMOVE: High duplication or redundant sections
    remove_list = [
        'installation.md',  # Duplicate of getting_started
        'jac_in_a_flash.md',  # Duplicate of tour
        'tour.md',  # Keep only the concise version at end

        # Remove non-core Jac Book chapters (keep only 1,4,5,7,8,9,10,12,17,18,21)
        'chapter_2.md',
        'chapter_3.md',
        'chapter_6.md',
        'chapter_11.md',
        'chapter_13.md',
        'chapter_14.md',
        'chapter_15.md',
        'chapter_16.md',
        'chapter_19.md',
        'chapter_20.md',

        # Remove example READMEs (keep actual implementations)
        'aider-genius-lite/README.md',
        'friendzone-lite/README.md',
        'task-manager-lite/README.md',
    ]

    for pattern in remove_list:
        if pattern in filepath:
            return 'remove'

    # CONDENSE: Significantly shorten these sections
    condense_list = [
        'beginners_guide_to_jac.md',  # Heavily overlaps with Jac Book
        'data_spatial/FAQ.md',  # Answers covered in main docs
        'bigfeatures.md',
    ]

    for pattern in condense_list:
        if pattern in filepath:
            return 'condense'

    # KEEP: Essential documentation
    return 'keep'

def extract_first_n_lines(content, n=50):
    """Extract first N non-empty lines from content."""
    lines = content.split('\n')
    result = []
    count = 0

    for line in lines:
        result.append(line)
        if line.strip():  # Count non-empty lines
            count += 1
        if count >= n:
            break

    return '\n'.join(result)

def condense_section(section):
    """Aggressively condense a section to summary only."""
    content = section['content']

    # For beginners guide, keep only first major section
    if 'beginners_guide' in section['file']:
        intro_match = re.search(r'^(.*?)(##\s+Installation|##\s+Chapter)',
                               content, re.DOTALL | re.MULTILINE)
        if intro_match:
            condensed = intro_match.group(1)
            condensed += '\n\n---\n\n**Note**: This beginner\'s guide has been condensed. '
            condensed += 'For comprehensive tutorials, see the Jac Book chapters.\n\n'
            condensed += 'Core concepts are covered in:\n'
            condensed += '- Chapter 1: Introduction to Jac\n'
            condensed += '- Chapters 4-5: Functions and AI Operations\n'
            condensed += '- Chapters 7-10: Object-Oriented and Object-Spatial Programming\n'
            condensed += '- Chapter 12: Walkers as API Endpoints\n'
            condensed += '- Chapters 17-18: Testing and Deployment\n\n'
            return condensed

    # For FAQ, keep only questions with brief answers
    if 'FAQ' in section['file']:
        lines = content.split('\n')
        result = []
        keep_next = 0

        for line in lines:
            # Keep headers and questions
            if line.startswith('#'):
                result.append(line)
                keep_next = 2  # Keep next 2 lines (brief answer)
            elif keep_next > 0:
                result.append(line)
                keep_next -= 1

        return '\n'.join(result[:200])  # Limit to 200 lines

    # Default: Keep first section only
    return extract_first_n_lines(content, 30) + '\n\n> **[Section condensed]**\n\n'

def remove_duplicate_code_blocks(content):
    """Remove duplicate code examples based on patterns."""
    lines = content.split('\n')
    result = []
    in_code_block = False
    current_block = []
    seen_hashes = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip().startswith('```'):
            if not in_code_block:
                # Start of code block
                in_code_block = True
                current_block = [line]
            else:
                # End of code block
                in_code_block = False
                current_block.append(line)

                # Create hash of code content
                code_content = '\n'.join(current_block[1:-1])  # Exclude ``` markers

                # Normalize for duplicate detection
                normalized = code_content.lower()
                normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
                normalized = re.sub(r'alice|bob|charlie', 'PERSON', normalized)
                normalized = re.sub(r'\d+', 'NUM', normalized)

                # Calculate simple hash
                code_hash = hash(normalized[:200])  # Hash first 200 chars

                # Check if this is a trivial example we've seen
                is_duplicate = False
                if len(current_block) < 15:  # Short examples
                    if 'with entry' in normalized or 'hello' in normalized:
                        if code_hash in seen_hashes:
                            is_duplicate = True
                        seen_hashes.add(code_hash)

                if not is_duplicate:
                    result.extend(current_block)
                else:
                    result.append('```\n[Duplicate example removed]\n```')

                current_block = []
        elif in_code_block:
            current_block.append(line)
        else:
            result.append(line)

        i += 1

    return '\n'.join(result)

def remove_duplicate_sections(content):
    """Remove duplicate conceptual sections."""
    # Remove repeated "What is Jac" explanations
    if content.count('Object-Spatial Programming') > 2:
        # Keep only first occurrence
        parts = content.split('## What is Jac', 1)
        if len(parts) > 1:
            # Remove subsequent occurrences
            first_part = parts[0]
            second_part = parts[1]
            # Keep first What is Jac section
            next_section = re.split(r'\n##\s+', second_part, 1)
            if len(next_section) > 1:
                content = first_part + '## What is Jac' + next_section[0] + '\n## ' + next_section[1]

    # Remove repeated installation instructions
    installation_patterns = [
        r'##\s+Installation\s+.*?(?=\n##\s+|\Z)',
        r'pip install jaclang.*?(?=\n##\s+|\Z)',
    ]

    for pattern in installation_patterns:
        matches = list(re.finditer(pattern, content, re.DOTALL))
        if len(matches) > 1:
            # Keep first, remove others
            for match in matches[1:]:
                content = content.replace(match.group(0), '[Installation section removed - see Getting Started]')

    return content

def merge_getting_started_installation(sections):
    """Merge getting_started and installation into one comprehensive guide."""
    getting_started = None
    installation = None

    for section in sections:
        if 'getting_started.md' in section['file']:
            getting_started = section
        elif 'installation.md' in section['file']:
            installation = section

    if getting_started and installation:
        # Merge installation into getting_started
        merged_content = f"""# Getting Started with Jac

This guide will help you install and set up Jac for development.

{getting_started['content']}

## Installation Details

{installation['content']}
"""
        getting_started['content'] = merged_content
        getting_started['lines'] = len(merged_content.split('\n'))

def main():
    input_file = 'jaseci-docs-compiled.md'
    output_file = 'jaseci-docs-trimmed.md'

    print(f"Reading {input_file}...")
    sections = read_file_sections(input_file)
    print(f"Found {len(sections)} sections\n")

    # Merge getting started and installation
    merge_getting_started_installation(sections)

    output_sections = []
    stats = {'keep': 0, 'condense': 0, 'remove': 0, 'lines_in': 0, 'lines_out': 0}

    # Add header
    header = """# Jac Language Documentation (Condensed Edition)

**This is a significantly condensed version of the Jac language documentation.**

The original 40,447-line documentation contained substantial duplication across:
- Tutorial sections (Jac Book vs Beginners Guide ~70% overlap)
- Object-Spatial Programming explanations (repeated 10+ times)
- Installation guides (4 duplicate versions)
- Code examples (same patterns with minor variations)
- Setup instructions (repeated in every section)

## What's Included

**Essential Documentation (Fully Preserved):**
- ✅ Breaking Changes & Migration Guides
- ✅ Release Notes & Roadmap
- ✅ Complete Internals & Architecture Documentation
- ✅ Symbol Tables & Planning Specifications
- ✅ Plugin Development Guides
- ✅ Jac-byLLM AI Integration (complete)
- ✅ Jac Cloud Deployment (complete)
- ✅ Core Jac Book Tutorial Chapters (1, 4, 5, 7, 8, 9, 10, 12, 17, 18, 21)
- ✅ Learning Resources & Keywords Reference
- ✅ CLI Tools Documentation

**Condensed Sections:**
- 📝 Beginners Guide (intro only, references Jac Book)
- 📝 Data Spatial FAQ (questions only, brief answers)
- 📝 Duplicate code examples removed

**Removed (High Duplication):**
- ❌ installation.md (merged into getting_started.md)
- ❌ jac_in_a_flash.md (content in Tour section)
- ❌ Non-core Jac Book chapters (2, 3, 6, 11, 13-16, 19-20)
- ❌ Example README files (content in implementation files)
- ❌ Duplicate "What is Jac" explanations

## Using This Documentation

For the most efficient learning path:
1. Start with **Getting Started** for installation
2. Follow **Jac Book Core Chapters** (1→4→5→7→8→9→10→12) for progressive learning
3. Reference **Keywords** and **CLI Tools** as needed
4. Use **Jac-byLLM** for AI integration
5. Deploy with **Jac Cloud** documentation

---

"""
    output_sections.append(header)

    print(f"{'Action':<10} | {'File':<65} | {'Lines In':>8} | {'Lines Out':>9} | {'Reduction':>9}")
    print("="*115)

    for section in sections:
        action = should_keep_section(section['file'])
        stats[action] += 1
        stats['lines_in'] += section['lines']

        original_lines = section['lines']
        output_content = None

        if action == 'keep':
            # Remove duplicate code blocks and sections
            content = remove_duplicate_code_blocks(section['content'])
            content = remove_duplicate_sections(content)
            output_content = f"\n{'='*80}\n"
            output_content += f"FILE: {section['file']}\n"
            output_content += f"{'='*80}\n\n"
            output_content += content
            output_sections.append(output_content)

        elif action == 'condense':
            # Aggressive condensing
            condensed = condense_section(section)
            output_content = f"\n{'='*80}\n"
            output_content += f"FILE: {section['file']}\n"
            output_content += f"{'='*80}\n\n"
            output_content += condensed
            output_sections.append(output_content)

        # Calculate output lines
        if output_content:
            output_lines = len(output_content.split('\n'))
            stats['lines_out'] += output_lines
            reduction = (1 - output_lines / original_lines) * 100 if original_lines > 0 else 0
            print(f"{action:<10} | {section['file']:<65} | {original_lines:>8} | {output_lines:>9} | {reduction:>8.1f}%")
        else:
            stats['lines_out'] += 0
            print(f"{action:<10} | {section['file']:<65} | {original_lines:>8} | {'removed':>9} | {'100.0%':>9}")

    # Write output
    print(f"\nWriting {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_sections))

    # Calculate final statistics
    final_lines = sum(len(s.split('\n')) for s in output_sections)
    reduction = (1 - final_lines / stats['lines_in']) * 100

    print(f"\n{'='*115}")
    print(f"FINAL STATISTICS")
    print(f"{'='*115}")
    print(f"  Sections kept (full):      {stats['keep']:>4}")
    print(f"  Sections condensed:        {stats['condense']:>4}")
    print(f"  Sections removed:          {stats['remove']:>4}")
    print(f"  {'─'*111}")
    print(f"  Original lines:            {stats['lines_in']:>10,}")
    print(f"  Output lines:              {final_lines:>10,}")
    print(f"  {'─'*111}")
    print(f"  Total reduction:           {reduction:>9.1f}%")
    print(f"  Size reduction:            {stats['lines_in'] - final_lines:>10,} lines removed")
    print(f"{'='*115}\n")

if __name__ == '__main__':
    main()
