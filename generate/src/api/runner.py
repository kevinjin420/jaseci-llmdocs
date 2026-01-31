#!/usr/bin/env python3
import asyncio
import json
import yaml
import shutil
import time
import traceback
import sys
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

import tiktoken

from ..pipeline.llm import LLM
from ..pipeline.sanitizer import Sanitizer
from ..pipeline.deterministic_extractor import DeterministicExtractor
from ..pipeline.assembler import Assembler
from ..pipeline.validator import Validator, JacCheckResult
from ..pipeline.scoring import QualityScorer


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
    progress: int = 0
    progress_total: int = 0
    progress_message: str = ""
    extra: dict = field(default_factory=dict)

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
    """
    Lossless documentation pipeline runner.

    Stages:
    1. Fetch & Sanitize - Get docs, clean, extract skeletons (deterministic)
    2. Extract - Categorize content, select best examples (deterministic)
    3. Assemble - Single LLM call to generate final reference
    """

    def __init__(self, config_path: Path, broadcast: Callable):
        self.root = Path(__file__).parents[2]
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        source_dir = Path(self.cfg['source_dir'])
        self.src = source_dir if source_dir.is_absolute() else self.root / source_dir
        self.broadcast = broadcast
        self.is_running = False
        self.validator = Validator()
        self.loop = None

        self.sanitized_dir = self.root / "output" / "0_sanitized"
        self.extracted_dir = self.root / "output" / "1_extracted"
        self.final_dir = self.root / "output" / "2_final"
        self.scores_dir = self.root / "scores"

        self.stages: dict[str, StageMetrics] = {
            "fetch": StageMetrics(name="Fetch & Sanitize"),
            "extract": StageMetrics(name="Deterministic Extract"),
            "assemble": StageMetrics(name="LLM Assembly"),
        }

        self.overall_start: Optional[float] = None
        self.overall_end: Optional[float] = None
        self.final_validation: Optional[dict] = None
        self.scorer = QualityScorer(self.scores_dir)

    async def emit(self, event: str, data: dict):
        await self.broadcast({
            "event": event,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })

    def _make_progress_callback(self, stage_name: str):
        stage = self.stages[stage_name]

        def callback(current: int, total: int, message: str = ""):
            stage.progress = current
            stage.progress_total = total
            stage.progress_message = message

            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.emit("progress", {
                        "stage": stage_name,
                        "current": current,
                        "total": total,
                        "message": message
                    }),
                    self.loop
                )

        return callback

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "stages": {k: v.status for k, v in self.stages.items()},
            "overall_start": self.overall_start,
            "overall_end": self.overall_end,
        }

    def get_metrics(self) -> dict:
        total_input = self.stages["fetch"].input_size
        total_output = self.stages["assemble"].output_size

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

    def _get_next_version(self) -> str:
        """Generate next version string based on timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def run(self):
        if self.is_running:
            return

        self.is_running = True
        self.loop = asyncio.get_event_loop()
        self.overall_start = time.time()

        for stage in self.stages.values():
            stage.status = "pending"
            stage.start_time = None
            stage.end_time = None
            stage.files = []
            stage.progress = 0
            stage.progress_total = 0
            stage.extra = {}

        await self.emit("pipeline_start", {"source": str(self.src)})

        try:
            out = self.root / "output"
            if out.exists():
                shutil.rmtree(out)

            await self._run_fetch()
            await self._run_extract()
            await self._run_assemble()

            self.overall_end = time.time()
            await self.emit("pipeline_complete", self.get_metrics())

        except Exception as e:
            await self.emit("pipeline_error", {"error": str(e)})
        finally:
            self.is_running = False

    async def run_stage(self, stage_name: str):
        if self.is_running:
            return

        self.is_running = True
        self.loop = asyncio.get_event_loop()

        stage = self.stages[stage_name]
        stage.status = "pending"
        stage.start_time = None
        stage.end_time = None
        stage.files = []
        stage.progress = 0
        stage.progress_total = 0

        await self.emit("pipeline_start", {"source": str(self.src), "single_stage": stage_name})

        try:
            stage_methods = {
                "fetch": self._run_fetch,
                "extract": self._run_extract,
                "assemble": self._run_assemble,
            }

            await stage_methods[stage_name]()
            await self.emit("pipeline_complete", {"stage": stage_name, "metrics": stage.to_dict()})

        except Exception as e:
            await self.emit("pipeline_error", {"error": str(e), "stage": stage_name})
        finally:
            self.is_running = False

    async def _run_fetch(self):
        """Stage 1: Fetch docs from sources and sanitize."""
        stage = self.stages["fetch"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "fetch"})

        try:
            sanitizer = Sanitizer(self.cfg)

            def fetch_progress(source_id: str, current: int, total: int):
                if self.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.emit("progress", {
                            "stage": "fetch",
                            "current": current,
                            "total": total,
                            "message": f"Fetching {source_id}..."
                        }),
                        self.loop
                    )

            stats = await asyncio.to_thread(
                sanitizer.run, self.src, self.sanitized_dir, fetch_progress
            )

            input_size = 0
            input_file_count = 0
            for source_stats in stats.get("sources", []):
                for f in source_stats.get("files", []):
                    input_size += f.get("size", 0)
                    input_file_count += 1

            stage.input_size = input_size
            stage.file_count = input_file_count

            out_files = list(self.sanitized_dir.rglob("*.md"))
            stage.output_size = sum(f.stat().st_size for f in out_files)
            stage.files = [
                {"name": f["path"], "size": f["cleaned_size"]}
                for f in stats.get("files", [])[:20]
            ]
            stage.extra = {
                "jac_files": stats.get("jac_files", 0),
                "jac_definitions": stats.get("jac_definitions", 0),
                "sources": len(stats.get("sources", [])),
            }

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {
                "stage": "fetch",
                "metrics": stage.to_dict(),
                "stats": {
                    "total": stats["total_files"],
                    "kept": stats["kept_files"],
                    "excluded": stats["excluded_files"],
                    "empty": stats["empty_files"],
                    "jac_files": stats.get("jac_files", 0),
                    "jac_definitions": stats.get("jac_definitions", 0),
                }
            })

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            print(f"\n[FETCH ERROR] {e}", file=sys.stderr)
            traceback.print_exc()
            await self.emit("stage_error", {"stage": "fetch", "error": str(e)})
            raise

    async def _run_extract(self):
        """Stage 2: Deterministic extraction - categorize and select examples."""
        stage = self.stages["extract"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "extract"})

        try:
            source_files = list(self.sanitized_dir.rglob("*.md"))
            stage.input_size = sum(f.stat().st_size for f in source_files)
            stage.file_count = len(source_files)

            progress_cb = self._make_progress_callback("extract")
            progress_cb(0, 3, "Initializing extractor...")

            extractor = DeterministicExtractor(self.cfg)

            progress_cb(1, 3, "Extracting signatures and examples...")
            extracted = await asyncio.to_thread(
                extractor.extract_from_directory, self.sanitized_dir
            )

            progress_cb(2, 3, "Selecting best examples...")
            best_examples = extractor.select_best_examples(extracted, max_per_type=3)

            progress_cb(3, 3, "Formatting output...")
            formatted = extractor.format_for_assembly(extracted)

            self.extracted_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.extracted_dir / "extracted_content.txt"
            output_path.write_text(formatted)

            stage.output_size = len(formatted)
            stage.files = [{"name": output_path.name, "size": stage.output_size}]
            stage.extra = {
                "signatures": extracted.total_signatures,
                "examples": extracted.total_examples,
                "selected_examples": sum(len(v) for v in best_examples.values()),
                "keywords_found": len(extracted.keywords_found),
                "construct_types": len(extracted.examples),
            }

            # Store for assembly stage
            self._extracted_content = extracted
            self._extractor = extractor

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {
                "stage": "extract",
                "metrics": stage.to_dict(),
                "stats": stage.extra
            })

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            print(f"\n[EXTRACT ERROR] {e}", file=sys.stderr)
            traceback.print_exc()
            await self.emit("stage_error", {"stage": "extract", "error": str(e)})
            raise

    async def _run_assemble(self):
        """Stage 3: Single LLM call to assemble final reference."""
        stage = self.stages["assemble"]
        stage.status = "running"
        stage.start_time = time.time()
        await self.emit("stage_start", {"stage": "assemble"})

        try:
            # Get extracted content
            if not hasattr(self, '_extracted_content'):
                extractor = DeterministicExtractor(self.cfg)
                self._extracted_content = extractor.extract_from_directory(self.sanitized_dir)
                self._extractor = extractor

            extracted_path = self.extracted_dir / "extracted_content.txt"
            stage.input_size = extracted_path.stat().st_size if extracted_path.exists() else 0

            progress_cb = self._make_progress_callback("assemble")

            token_buffer = []
            last_emit_time = [time.time()]

            def on_token(token: str):
                token_buffer.append(token)
                now = time.time()
                if now - last_emit_time[0] > 0.1 or len(token_buffer) > 50:
                    if self.loop:
                        chunk = ''.join(token_buffer)
                        token_buffer.clear()
                        last_emit_time[0] = now
                        asyncio.run_coroutine_threadsafe(
                            self.emit("llm_token", {"stage": "assemble", "token": chunk}),
                            self.loop
                        )

            llm = LLM(self.cfg, self.cfg.get('assembly', {}))
            assembler = Assembler(llm, self.cfg, on_progress=progress_cb, on_token=on_token)

            result = await asyncio.to_thread(
                assembler.assemble, self._extracted_content, self._extractor
            )

            if token_buffer:
                await self.emit("llm_token", {"stage": "assemble", "token": ''.join(token_buffer)})

            self.final_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.final_dir / "jac_reference.txt"
            output_path.write_text(result)

            # Also save to release
            release_dir = self.root.parent / "release"
            release_dir.mkdir(exist_ok=True)
            (release_dir / "candidate.txt").write_text(result)

            # Run jac check before saving validation (will be added to final_validation below)

            stage.output_size = len(result)
            stage.files = [{"name": output_path.name, "size": stage.output_size}]

            # Validate patterns
            validation_result = self.validator.validate_final(result)
            patterns = self.validator.find_patterns(result)

            # Count tokens using tiktoken (cl100k_base is used by GPT-4, Claude uses similar)
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                token_count = len(enc.encode(result))
            except Exception:
                token_count = len(result) // 4  # rough estimate fallback

            # Run jac check on all code examples
            progress_cb(0, 1, "Running jac check on code examples...")
            jac_check_result = self.validator.jac_check_examples(
                result,
                max_errors=10,
                on_progress=lambda c, t, m: progress_cb(c, t, f"jac check: {m}")
            )

            version = self._get_next_version()
            quality_score = self.scorer.score(
                result, version,
                jac_check_result=jac_check_result,
                patterns_found=patterns,
                token_count=token_count
            )

            baseline = self.scorer.get_baseline()
            if baseline:
                quality_score.regressions, quality_score.improvements = self.scorer.compare(
                    quality_score, baseline
                )

            self.scorer.save_score(quality_score)

            self.final_validation = {
                "is_valid": validation_result.is_valid and jac_check_result.pass_rate >= 80,
                "issues": validation_result.issues,
                "missing_patterns": validation_result.missing_patterns,
                "patterns_found": len(patterns),
                "patterns_total": len(self.validator.CRITICAL_PATTERNS),
                "output_size": len(result),
                "token_count": token_count,
                "jac_check": {
                    "total_blocks": jac_check_result.total_blocks,
                    "passed": jac_check_result.passed,
                    "failed": jac_check_result.failed,
                    "skipped": jac_check_result.skipped,
                    "pass_rate": jac_check_result.pass_rate,
                    "errors": jac_check_result.errors,
                },
                "quality_score": {
                    "version": quality_score.version,
                    "timestamp": quality_score.timestamp,
                    "content_hash": quality_score.content_hash,
                    "pattern_coverage": quality_score.pattern_coverage,
                    "constructs": quality_score.constructs,
                    "regressions": quality_score.regressions,
                    "improvements": quality_score.improvements,
                },
            }

            # Save validation results as JSON
            validation_json_path = release_dir / "candidate.validation.json"
            validation_json_path.write_text(json.dumps(self.final_validation, indent=2))

            stage.extra = {
                "validation": self.final_validation,
                "output_path": str(output_path),
                "release_path": str(release_dir / "candidate.txt"),
                "validation_path": str(validation_json_path),
            }

            stage.status = "complete"
            stage.end_time = time.time()
            await self.emit("stage_complete", {
                "stage": "assemble",
                "metrics": stage.to_dict(),
                "validation": self.final_validation
            })

        except Exception as e:
            stage.status = "error"
            stage.error = str(e)
            stage.end_time = time.time()
            print(f"\n[ASSEMBLE ERROR] {e}", file=sys.stderr)
            traceback.print_exc()
            await self.emit("stage_error", {"stage": "assemble", "error": str(e)})
            raise
