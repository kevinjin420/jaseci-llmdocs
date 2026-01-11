#!/usr/bin/env python3
import asyncio
import yaml
import shutil
import time
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from ..pipeline.llm import LLM
from ..pipeline.stage1_extract import Extractor
from ..pipeline.stage2_merge import Merger
from ..pipeline.stage3_reduce import Reducer
from ..pipeline.stage4_compress import Compressor
from ..pipeline.validator import Validator


@dataclass
class StageMetrics:
    name: str
    status: str = "pending"
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    input_size: int = 0
    output_size: int = 0
    file_count: int = 0
    files: list = field(default_factory=list)
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0

    @property
    def compression_ratio(self) -> float:
        if self.input_size > 0:
            return self.output_size / self.input_size
        return 1.0

    def to_dict(self):
        d = asdict(self)
        d['duration'] = self.duration
        d['compression_ratio'] = self.compression_ratio
        return d


class PipelineRunner:
    def __init__(self, config_path: Path, broadcast: Callable):
        self.root = Path(__file__).parents[2]
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        source_dir = Path(self.cfg['source_dir'])
        self.src = source_dir if source_dir.is_absolute() else self.root / source_dir
        self.broadcast = broadcast
        self.is_running = False
        self.validator = Validator()

        self.stages: dict[str, StageMetrics] = {
            "extract": StageMetrics(name="Topic Extraction"),
            "merge": StageMetrics(name="Topic Merging"),
            "reduce": StageMetrics(name="Hierarchical Reduction"),
            "compress": StageMetrics(name="Final Minification"),
        }

        self.overall_start: Optional[float] = None
        self.overall_end: Optional[float] = None
        self.final_validation: Optional[dict] = None

    async def emit(self, event: str, data: dict):
        await self.broadcast({
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "stages": {k: v.status for k, v in self.stages.items()},
            "overall_start": self.overall_start,
            "overall_end": self.overall_end,
        }

    def get_metrics(self) -> dict:
        total_input = self.stages["extract"].input_size
        total_output = self.stages["compress"].output_size

        return {
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "total_input_size": total_input,
            "total_output_size": total_output,
            "overall_compression": total_output / total_input if total_input > 0 else 0,
            "total_duration": (self.overall_end or time.time()) - (self.overall_start or time.time()),
            "validation": self.final_validation,
        }

    def get_stage_details(self) -> list:
        return [v.to_dict() for v in self.stages.values()]

    async def run(self):
        if self.is_running:
            return

        self.is_running = True
        self.overall_start = time.time()

        for stage in self.stages.values():
            stage.status = "pending"
            stage.start_time = None
            stage.end_time = None
            stage.files = []

        await self.emit("pipeline_start", {"source": str(self.src)})

        try:
            out = self.root / "output"
            if out.exists():
                shutil.rmtree(out)

            await self._run_extract()
            await self._run_merge()
            await self._run_reduce()
            await self._run_compress()

            self.overall_end = time.time()
            await self.emit("pipeline_complete", self.get_metrics())

        except Exception as e:
            await self.emit("pipeline_error", {"error": str(e)})
        finally:
            self.is_running = False

    async def _run_extract(self):
        stage = self.stages["extract"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "extract"})

        try:
            source_files = list(self.src.rglob("*.md"))
            stage.input_size = sum(f.stat().st_size for f in source_files)
            stage.file_count = len(source_files)

            extractor = Extractor(LLM(self.cfg, self.cfg.get('extraction')), self.cfg)
            await asyncio.to_thread(
                extractor.run, self.src, self.cfg['processing'].get('skip_patterns')
            )

            out_dir = self.root / self.cfg['extraction']['output_dir']
            if out_dir.exists():
                out_files = list(out_dir.glob("*.md"))
                stage.output_size = sum(f.stat().st_size for f in out_files)
                stage.files = [
                    {"name": f.name, "size": f.stat().st_size}
                    for f in sorted(out_files, key=lambda x: x.stat().st_size, reverse=True)
                ]

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {"stage": "extract", "metrics": stage.to_dict()})

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            await self.emit("stage_error", {"stage": "extract", "error": str(e)})
            raise

    async def _run_merge(self):
        stage = self.stages["merge"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "merge"})

        try:
            in_dir = self.root / self.cfg['extraction']['output_dir']
            in_files = list(in_dir.glob("*.md"))
            stage.input_size = sum(f.stat().st_size for f in in_files)
            stage.file_count = len(in_files)

            merger = Merger(LLM(self.cfg, self.cfg.get('merge')), self.cfg)
            await asyncio.to_thread(merger.run)

            out_dir = self.root / self.cfg['merge']['output_dir']
            if out_dir.exists():
                out_files = list(out_dir.glob("*.txt"))
                stage.output_size = sum(f.stat().st_size for f in out_files)
                stage.files = [
                    {"name": f.name, "size": f.stat().st_size}
                    for f in sorted(out_files, key=lambda x: x.stat().st_size, reverse=True)
                ]

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {"stage": "merge", "metrics": stage.to_dict()})

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            await self.emit("stage_error", {"stage": "merge", "error": str(e)})
            raise

    async def _run_reduce(self):
        stage = self.stages["reduce"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "reduce"})

        try:
            in_dir = self.root / self.cfg['merge']['output_dir']
            in_files = list(in_dir.glob("*.txt"))
            stage.input_size = sum(f.stat().st_size for f in in_files)
            stage.file_count = len(in_files)

            reducer = Reducer(LLM(self.cfg, self.cfg.get('hierarchical_merge')), self.cfg)
            result = await asyncio.to_thread(
                reducer.run, self.cfg['hierarchical_merge']['ratio']
            )

            if result:
                out_path = Path(result['output_path'])
                stage.output_size = out_path.stat().st_size
                stage.files = [{"name": out_path.name, "size": stage.output_size}]

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {"stage": "reduce", "metrics": stage.to_dict()})

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            await self.emit("stage_error", {"stage": "reduce", "error": str(e)})
            raise

    async def _run_compress(self):
        stage = self.stages["compress"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "compress"})

        try:
            in_path = self.root / self.cfg['hierarchical_merge']['output_dir'] / "unified_doc.txt"
            stage.input_size = in_path.stat().st_size

            compressor = Compressor(None, self.cfg)
            await asyncio.to_thread(compressor.run, in_path, "jac_docs_final.txt")

            out_path = self.root / self.cfg['ultra_compression']['output_dir'] / "jac_docs_final.txt"
            if out_path.exists():
                stage.output_size = out_path.stat().st_size
                stage.files = [{"name": out_path.name, "size": stage.output_size}]

                content = out_path.read_text()
                result = self.validator.validate_final(content)
                patterns = self.validator.find_patterns(content)

                self.final_validation = {
                    "is_valid": result.is_valid,
                    "issues": result.issues,
                    "missing_patterns": result.missing_patterns,
                    "patterns_found": len(patterns),
                    "patterns_total": len(self.validator.CRITICAL_PATTERNS),
                }

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {
                "stage": "compress",
                "metrics": stage.to_dict(),
                "validation": self.final_validation
            })

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            await self.emit("stage_error", {"stage": "compress", "error": str(e)})
            raise
