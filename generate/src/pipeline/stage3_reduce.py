import math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from .llm import LLM
from .validator import Validator


class Reducer:
    def __init__(self, llm: LLM, config: dict):
        self.llm = llm
        self.in_dir = Path(config.get('merge', {}).get('output_dir', 'output/2_merged'))
        self.out_dir = Path(config.get('hierarchical_merge', {}).get('output_dir', 'output/3_hierarchical'))
        self.out_dir.mkdir(parents=True, exist_ok=True)

        hier_cfg = config.get('hierarchical_merge', {})
        self.max_passes = hier_cfg.get('max_passes', 2)
        self.min_pattern_ratio = hier_cfg.get('min_pattern_ratio', 0.7)

        self.validator = Validator(min_size_ratio=0.1, required_pattern_ratio=self.min_pattern_ratio)

        root = Path(__file__).parents[2]
        prompt_path = root / "config/merge_prompt.txt"
        if not prompt_path.exists():
            prompt_path = root / "config/stage3_reduce_prompt.txt"
        with open(prompt_path) as f:
            self.prompt = f.read()

    def run(self, ratio=4):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(self.in_dir.glob("*.txt"))
        if not files:
            return None

        print(f"Stage 3: Reducing {len(files)} files (Ratio {ratio}:1, max {self.max_passes} passes)...")
        current = [f.read_text() for f in files]
        combined_input = "\n\n".join(current)

        pass_num = 0
        while len(current) > 1 and pass_num < self.max_passes:
            pass_num += 1
            target_count = max(1, math.ceil(len(current) / ratio))
            print(f"  Pass {pass_num}: {len(current)} -> {target_count}")

            groups = ["\n\n".join(current[i:i+ratio]) for i in range(0, len(current), ratio)]

            with ThreadPoolExecutor(max_workers=8) as pool:
                next_level = list(pool.map(self.merge_group, groups))

            next_level = [r for r in next_level if r and r.strip()]

            if not next_level:
                print(f"  Pass {pass_num} produced empty output, stopping")
                break

            combined_output = "\n\n".join(next_level)
            result = self.validator.validate(combined_input, combined_output)

            if not result.is_valid:
                print(f"  Pass {pass_num} validation failed: {result.issues}")
                if result.missing_patterns:
                    print(f"    Missing patterns: {result.missing_patterns[:5]}")
                print(f"  Stopping reduction early to preserve content")
                break

            print(f"    Size: {len(combined_input)} -> {len(combined_output)} ({result.size_ratio:.1%})")
            current = next_level
            combined_input = combined_output

        if len(current) > 1:
            print(f"  Final merge: combining {len(current)} remaining files...")
            final = self.merge_group("\n\n".join(current))
            if final and final.strip():
                final_result = self.validator.validate(combined_input, final)
                if final_result.is_valid:
                    current = [final]
                else:
                    print(f"  Final merge lost content, keeping {len(current)} separate sections")
                    current = [combined_input]
            else:
                current = [combined_input]

        out_path = self.out_dir / "unified_doc.txt"
        output = current[0] if len(current) == 1 else "\n\n".join(current)
        out_path.write_text(output)
        print(f"  Saved to {out_path} ({len(output)} chars)")
        return {'success': True, 'output_path': str(out_path)}

    def merge_group(self, content):
        try:
            result = self.llm.query(content, self.prompt)
            return result if result else content
        except Exception as e:
            print(f"  Merge error: {e}")
            return content
