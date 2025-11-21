"""JSON repair and handling utilities"""

import re


def repair_json(json_str: str) -> str:
    """Attempt to repair common JSON syntax errors"""
    json_str = json_str.strip()

    json_str = json_str.replace('```json', '').replace('```', '').strip()

    lines = json_str.split('\n')
    repaired_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            repaired_lines.append(line)
            continue

        if '":' in stripped and stripped.count('"') % 2 != 0:
            if not stripped.endswith('"') and not stripped.endswith('",'):
                line = line.rstrip() + '"'
                stripped = line.strip()

        if stripped.endswith('"') and not stripped.endswith('",') and not stripped.endswith('"}'):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('"') or next_line.startswith('}'):
                    line = line.rstrip() + ','

        repaired_lines.append(line)

    json_str = '\n'.join(repaired_lines)

    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')

    if open_braces > close_braces:
        json_str += '\n' + '}' * (open_braces - close_braces)

    if open_brackets > close_brackets:
        json_str += '\n' + ']' * (open_brackets - close_brackets)

    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

    return json_str
