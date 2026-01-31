#!/usr/bin/env python3
"""Quality scoring system for pipeline outputs.

Provides benchmarking and regression detection for generated documentation.
"""
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .validator import Validator, JacCheckResult


@dataclass
class ConstructCoverage:
    construct: str
    examples_found: int
    examples_valid: int


@dataclass
class QualityScore:
    version: str
    timestamp: str
    content_hash: str
    patterns_found: int
    patterns_total: int
    pattern_coverage: float
    jac_check_passed: int
    jac_check_failed: int
    jac_check_rate: float
    constructs: list = field(default_factory=list)
    output_size: int = 0
    token_count: int = 0
    regressions: list = field(default_factory=list)
    improvements: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class QualityScorer:
    """Scores documentation quality and detects regressions."""

    REQUIRED_CONSTRUCTS = [
        'node', 'edge', 'walker', 'obj', 'can', 'spawn', 'visit', 'by_llm'
    ]

    def __init__(self, scores_dir: Path):
        self.scores_dir = scores_dir
        self.scores_dir.mkdir(parents=True, exist_ok=True)
        self.validator = Validator()
        self.history_file = scores_dir / "score_history.json"

    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _count_construct_examples(self, text: str) -> dict:
        """Count examples for each required construct."""
        import re
        counts = {}
        for construct in self.REQUIRED_CONSTRUCTS:
            pattern = rf'\b{construct}\s+\w+'
            matches = re.findall(pattern, text, re.IGNORECASE)
            counts[construct] = len(matches)
        return counts

    def _estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4

    def score(
        self,
        text: str,
        version: str,
        jac_check_result: JacCheckResult = None,
        patterns_found: set = None,
        token_count: int = None
    ) -> QualityScore:
        """Score documentation quality.

        Args:
            text: The documentation text to score
            version: Version identifier
            jac_check_result: Pre-computed jac check result (avoids recomputation)
            patterns_found: Pre-computed patterns (avoids recomputation)
            token_count: Pre-computed token count (avoids recomputation)
        """
        if patterns_found is None:
            patterns_found = self.validator.find_patterns(text)
        patterns_total = len(self.validator.CRITICAL_PATTERNS)

        if jac_check_result is None:
            jac_check_result = self.validator.jac_check_examples(text)

        if token_count is None:
            token_count = self._estimate_tokens(text)

        construct_counts = self._count_construct_examples(text)
        constructs = [
            ConstructCoverage(
                construct=c,
                examples_found=construct_counts.get(c, 0),
                examples_valid=0
            )
            for c in self.REQUIRED_CONSTRUCTS
        ]

        return QualityScore(
            version=version,
            timestamp=datetime.now().isoformat(),
            content_hash=self._compute_hash(text),
            patterns_found=len(patterns_found),
            patterns_total=patterns_total,
            pattern_coverage=len(patterns_found) / patterns_total if patterns_total > 0 else 0,
            jac_check_passed=jac_check_result.passed,
            jac_check_failed=jac_check_result.failed,
            jac_check_rate=jac_check_result.pass_rate,
            constructs=[asdict(c) for c in constructs],
            output_size=len(text),
            token_count=token_count,
        )

    def compare(
        self,
        current: QualityScore,
        baseline: QualityScore
    ) -> tuple[list, list]:
        """Compare current score against baseline, return (regressions, improvements)."""
        regressions = []
        improvements = []

        if current.pattern_coverage < baseline.pattern_coverage - 0.05:
            regressions.append(
                f"Pattern coverage dropped: {baseline.pattern_coverage:.1%} -> {current.pattern_coverage:.1%}"
            )
        elif current.pattern_coverage > baseline.pattern_coverage + 0.05:
            improvements.append(
                f"Pattern coverage improved: {baseline.pattern_coverage:.1%} -> {current.pattern_coverage:.1%}"
            )

        if current.jac_check_rate < baseline.jac_check_rate - 5:
            regressions.append(
                f"Jac check rate dropped: {baseline.jac_check_rate:.1f}% -> {current.jac_check_rate:.1f}%"
            )
        elif current.jac_check_rate > baseline.jac_check_rate + 5:
            improvements.append(
                f"Jac check rate improved: {baseline.jac_check_rate:.1f}% -> {current.jac_check_rate:.1f}%"
            )

        if current.output_size < baseline.output_size * 0.8:
            regressions.append(
                f"Output size decreased significantly: {baseline.output_size:,} -> {current.output_size:,} bytes"
            )

        baseline_constructs = {c['construct']: c['examples_found'] for c in baseline.constructs}
        current_constructs = {c['construct']: c['examples_found'] for c in current.constructs}

        for construct in self.REQUIRED_CONSTRUCTS:
            baseline_count = baseline_constructs.get(construct, 0)
            current_count = current_constructs.get(construct, 0)
            if baseline_count > 0 and current_count == 0:
                regressions.append(f"Lost all {construct} examples")
            elif baseline_count == 0 and current_count > 0:
                improvements.append(f"Added {construct} examples ({current_count})")

        return regressions, improvements

    def save_score(self, score: QualityScore):
        """Save score to history."""
        history = self.load_history()
        history.append(score.to_dict())

        if len(history) > 100:
            history = history[-100:]

        self.history_file.write_text(json.dumps(history, indent=2))

        version_file = self.scores_dir / f"score_{score.version}.json"
        version_file.write_text(json.dumps(score.to_dict(), indent=2))

    def load_history(self) -> list[dict]:
        """Load score history."""
        if not self.history_file.exists():
            return []
        try:
            return json.loads(self.history_file.read_text())
        except Exception:
            return []

    def get_baseline(self, version: str = None) -> Optional[QualityScore]:
        """Get baseline score for comparison."""
        history = self.load_history()
        if not history:
            return None

        if version:
            for entry in reversed(history):
                if entry.get('version') == version:
                    return self._dict_to_score(entry)
            return None

        return self._dict_to_score(history[-1])

    def get_score(self, version: str) -> Optional[QualityScore]:
        """Get score for a specific version."""
        version_file = self.scores_dir / f"score_{version}.json"
        if not version_file.exists():
            return None
        try:
            data = json.loads(version_file.read_text())
            return self._dict_to_score(data)
        except Exception:
            return None

    def _dict_to_score(self, data: dict) -> QualityScore:
        """Convert dict to QualityScore."""
        return QualityScore(
            version=data.get('version', ''),
            timestamp=data.get('timestamp', ''),
            content_hash=data.get('content_hash', ''),
            patterns_found=data.get('patterns_found', 0),
            patterns_total=data.get('patterns_total', 0),
            pattern_coverage=data.get('pattern_coverage', 0),
            jac_check_passed=data.get('jac_check_passed', 0),
            jac_check_failed=data.get('jac_check_failed', 0),
            jac_check_rate=data.get('jac_check_rate', 0),
            constructs=data.get('constructs', []),
            output_size=data.get('output_size', 0),
            token_count=data.get('token_count', 0),
            regressions=data.get('regressions', []),
            improvements=data.get('improvements', []),
        )

    def list_scores(self) -> list[dict]:
        """List all scores with summary info."""
        history = self.load_history()
        return [
            {
                'version': h.get('version'),
                'timestamp': h.get('timestamp'),
                'pattern_coverage': h.get('pattern_coverage'),
                'jac_check_rate': h.get('jac_check_rate'),
                'output_size': h.get('output_size'),
            }
            for h in history
        ]
