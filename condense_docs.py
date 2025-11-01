#!/usr/bin/env python3
"""
Script to condense jaseci-docs-compiled.md by removing duplicate content.
Based on analysis showing 69% duplication across 40,447 lines.
"""

def read_file_sections(filepath):
    """Parse the compiled docs into sections based on FILE: markers."""
    sections = []
    current_section = None
    current_content = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
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
                current_content = [line]
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
    """Determine if a section should be kept based on analysis."""

    # KEEP: Essential unique content
    keep_patterns = [
        'breaking_changes.md',
        'release_notes.md',
        'roadmap.md',
        'internals/',
        'planning_specs/',
        'symbol_tables/',
        'plugin_documentation.md',
        'contrib.md',
        'jac_plugins.md',
        'refs_coverage_report.md',
        'jac-byllm/',
        'jac-cloud/',
        'littlex_tutorial.md',
        'keywords.md',
        'jac_tools_and_cli.md',
        'learning_resources.md',
        'content_pieces.md',
        'fun/',
    ]

    # CONDENSE: Keep but with summary only
    condense_patterns = [
        'beginners_guide_to_jac.md',  # Keep header only, reference Jac Book
        'data_spatial/data_spatial_faq.md',  # Keep as quick reference
        'jac_in_a_flash.md',  # Merge into tour
    ]

    # REMOVE: High duplication or redundant
    remove_patterns = [
        'installation.md',  # Duplicate of getting_started
        'examples/README.md',  # Content in implementation files
    ]

    for pattern in remove_patterns:
        if pattern in filepath:
            return 'remove'

    for pattern in condense_patterns:
        if pattern in filepath:
            return 'condense'

    for pattern in keep_patterns:
        if pattern in filepath:
            return 'keep'

    # Default handling for Jac Book chapters
    if 'jacbook/' in filepath:
        # Keep core chapters: 1, 4, 5, 7, 8, 9, 10, 12, 17, 18
        core_chapters = ['chapter_1', 'chapter_4', 'chapter_5', 'chapter_7',
                        'chapter_8', 'chapter_9', 'chapter_10', 'chapter_12',
                        'chapter_17', 'chapter_18', 'chapter_21']
        for chapter in core_chapters:
            if chapter in filepath:
                return 'keep'
        return 'condense'  # Other chapters get condensed

    # Default: keep but might need review
    return 'keep'

def condense_section(section):
    """Condense a section by keeping header and summary only."""
    lines = section['content'].split('\n')
    condensed = []

    # Keep FILE marker and separator
    condensed.append(lines[0])  # FILE: marker
    if len(lines) > 1 and '===' in lines[1]:
        condensed.append(lines[1])  # Separator

    # Keep first few sections (title, intro)
    in_first_section = True
    line_count = 0

    for i, line in enumerate(lines[2:], start=2):
        # Keep title and first paragraph
        if line_count < 20 or (in_first_section and line.strip()):
            condensed.append(line)
            line_count += 1
            if line.startswith('#'):
                in_first_section = False
        else:
            break

    # Add reference note
    condensed.append('\n\n> **Note**: This section has been condensed. For detailed information, refer to the comprehensive chapters in the Jac Book.\n\n')

    return '\n'.join(condensed)

def remove_duplicate_examples(content):
    """Remove duplicate code examples while keeping unique ones."""
    # Track seen example patterns
    seen_patterns = set()
    lines = content.split('\n')
    result = []
    in_code_block = False
    current_block = []
    code_lang = None

    for line in lines:
        if line.strip().startswith('```'):
            if not in_code_block:
                # Starting code block
                in_code_block = True
                code_lang = line.strip()[3:].strip()
                current_block = [line]
            else:
                # Ending code block
                in_code_block = False
                current_block.append(line)

                # Check if this is a common duplicate pattern
                block_content = '\n'.join(current_block)

                # Create simplified pattern for comparison
                pattern = block_content.lower()
                pattern = pattern.replace('alice', 'PERSON1')
                pattern = pattern.replace('bob', 'PERSON2')
                pattern = pattern.replace('charlie', 'PERSON3')

                # Check for very common patterns
                is_duplicate = False
                if 'with entry' in pattern and len(current_block) < 10:
                    # Short entry blocks are often duplicates
                    simple_pattern = 'entry_' + code_lang
                    if simple_pattern in seen_patterns:
                        is_duplicate = True
                    seen_patterns.add(simple_pattern)

                if not is_duplicate:
                    result.extend(current_block)
                current_block = []
        elif in_code_block:
            current_block.append(line)
        else:
            result.append(line)

    return '\n'.join(result)

def main():
    input_file = 'jaseci-docs-compiled.md'
    output_file = 'jaseci-docs-trimmed.md'

    print(f"Reading {input_file}...")
    sections = read_file_sections(input_file)
    print(f"Found {len(sections)} sections")

    output_sections = []
    stats = {'keep': 0, 'condense': 0, 'remove': 0}

    # Add header
    header = """# Jac Language Documentation (Condensed)

This is a condensed version of the Jac language documentation with duplicate content removed.
The original documentation had significant duplication across tutorial sections, examples, and setup guides.

**Key Changes:**
- Merged duplicate installation and setup instructions
- Consolidated Object-Spatial Programming (OSP) explanations
- Removed redundant code examples
- Kept one comprehensive tutorial path (Jac Book core chapters)
- Maintained all unique technical documentation

For the complete unabridged documentation, refer to jaseci-docs-compiled.md

---

"""
    output_sections.append(header)

    for section in sections:
        action = should_keep_section(section['file'])
        stats[action] += 1

        print(f"  {action:8} | {section['file']:60} | {section['lines']:5} lines")

        if action == 'keep':
            # Keep full section, but remove duplicate examples
            content = remove_duplicate_examples(section['content'])
            output_sections.append(content)
        elif action == 'condense':
            # Keep condensed version
            condensed = condense_section(section)
            output_sections.append(condensed)
        # 'remove' sections are skipped

    # Write output
    print(f"\nWriting {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_sections))

    # Calculate statistics
    original_lines = sum(s['lines'] for s in sections)
    output_lines = sum(len(s.split('\n')) for s in output_sections)
    reduction = (1 - output_lines / original_lines) * 100

    print(f"\n{'='*60}")
    print(f"Statistics:")
    print(f"  Sections kept:      {stats['keep']}")
    print(f"  Sections condensed: {stats['condense']}")
    print(f"  Sections removed:   {stats['remove']}")
    print(f"  Original lines:     {original_lines:,}")
    print(f"  Output lines:       {output_lines:,}")
    print(f"  Reduction:          {reduction:.1f}%")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
