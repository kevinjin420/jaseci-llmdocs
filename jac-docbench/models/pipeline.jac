"""Pipeline state management node."""

import:py from time import time;

node PipelineState {
    has is_running: bool = False;
    has overall_start: float | None = None;
    has overall_end: float | None = None;
    has final_validation: dict | None = None;
    has current_stage: str | None = None;
    has error: str | None = None;

    can start() {
        self.is_running = True;
        self.overall_start = time();
        self.overall_end = None;
        self.error = None;
        self.final_validation = None;
    }

    can complete(validation: dict | None = None) {
        self.is_running = False;
        self.overall_end = time();
        self.final_validation = validation;
        self.current_stage = None;
    }

    can fail(error: str) {
        self.is_running = False;
        self.overall_end = time();
        self.error = error;
        self.current_stage = None;
    }

    can set_stage(stage_name: str) {
        self.current_stage = stage_name;
    }

    can get_duration() -> float | None {
        if self.overall_start is not None and self.overall_end is not None {
            return self.overall_end - self.overall_start;
        }
        return None;
    }

    can reset() {
        self.is_running = False;
        self.overall_start = None;
        self.overall_end = None;
        self.final_validation = None;
        self.current_stage = None;
        self.error = None;
    }

    can to_dict() -> dict {
        return {
            "is_running": self.is_running,
            "overall_start": self.overall_start,
            "overall_end": self.overall_end,
            "duration": self.get_duration(),
            "current_stage": self.current_stage,
            "error": self.error,
            "final_validation": self.final_validation
        };
    }
}

edge HasPipeline {}
