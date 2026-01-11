#!/usr/bin/env python3
import sys
import yaml
import shutil
from pathlib import Path

from .llm import LLM
from .stage1_extract import Extractor
from .stage2_merge import Merger
from .stage3_reduce import Reducer
from .stage4_compress import Compressor
from .validator import Validator


class Pipeline:
    def __init__(self, cfg_path):
        self.root = Path(__file__).parents[2]
        with open(cfg_path) as f:
            self.cfg = yaml.safe_load(f)
        source_dir = Path(self.cfg['source_dir'])
        self.src = source_dir if source_dir.is_absolute() else self.root / source_dir
        self.validator = Validator()

        self.extractor = Extractor(LLM(self.cfg, self.cfg.get('extraction')), self.cfg)
        self.merger = Merger(LLM(self.cfg, self.cfg.get('merge')), self.cfg)
        self.reducer = Reducer(LLM(self.cfg, self.cfg.get('hierarchical_merge')), self.cfg)
        self.compressor = Compressor(None, self.cfg)

    def run(self):
        out = self.root / "output"
        if out.exists():
            shutil.rmtree(out)

        print("=" * 50)
        print("Documentation Pipeline")
        print("=" * 50)

        self.extractor.run(self.src, self.cfg['processing'].get('skip_patterns'))
        self.merger.run()
        res = self.reducer.run(self.cfg['hierarchical_merge']['ratio'])

        if res:
            self.compressor.run(Path(res['output_path']), "jac_docs_final.txt")
            self.release()
            self.print_summary()

    def release(self):
        rel_dir = self.root.parent / "release" / "0.5"
        rel_dir.mkdir(parents=True, exist_ok=True)

        src = self.compressor.out_dir / "jac_docs_final.txt"
        if not src.exists():
            return

        nums = [
            int(f.stem.replace("jac_docs_final", "") or 1)
            for f in rel_dir.glob("jac_docs_final*.txt")
            if f.stem.replace("jac_docs_final", "").isdigit() or f.stem == "jac_docs_final"
        ]

        ver = max(nums) + 1 if nums else 1
        dest = rel_dir / f"jac_docs_final{ver}.txt"
        shutil.copy(src, dest)
        print(f"\nStage 5: Released to {dest}")

    def print_summary(self):
        print("\n" + "=" * 50)
        print("Pipeline Summary")
        print("=" * 50)

        final_path = self.compressor.out_dir / "jac_docs_final.txt"
        if final_path.exists():
            content = final_path.read_text()
            result = self.validator.validate_final(content)

            print(f"Final output: {len(content):,} chars, {len(content.split(chr(10))):,} lines")

            patterns_found = self.validator.find_patterns(content)
            print(f"Patterns preserved: {len(patterns_found)}/{len(self.validator.CRITICAL_PATTERNS)}")

            if result.missing_patterns:
                print(f"Missing patterns: {result.missing_patterns}")

            if result.issues:
                print(f"Issues: {result.issues}")
            else:
                print("Validation: PASSED")


if __name__ == '__main__':
    default_config = Path(__file__).parents[2] / "config" / "config.yaml"
    Pipeline(sys.argv[1] if len(sys.argv) > 1 else default_config).run()
