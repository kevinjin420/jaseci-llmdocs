"""Stage metrics nodes for pipeline tracking."""

import:py from time import time;

enum StageStatus {
    PENDING = "pending",
    RUNNING = "running",
    COMPLETE = "complete",
    ERROR = "error"
}

node StageMetrics {
    has name: str;
    has status: StageStatus = StageStatus.PENDING;
    has start_time: float | None = None;
    has end_time: float | None = None;
    has input_size: int = 0;
    has output_size: int = 0;
    has file_count: int = 0;
    has files: list[dict] = [];
    has progress: int = 0;
    has progress_total: int = 0;
    has progress_message: str = "";
    has error_message: str | None = None;

    can start() {
        self.status = StageStatus.RUNNING;
        self.start_time = time();
        self.end_time = None;
        self.progress = 0;
        self.error_message = None;
    }

    can complete() {
        self.status = StageStatus.COMPLETE;
        self.end_time = time();
        self.progress = self.progress_total if self.progress_total > 0 else 100;
    }

    can fail(error: str) {
        self.status = StageStatus.ERROR;
        self.end_time = time();
        self.error_message = error;
    }

    can update_progress(current: int, total: int, message: str = "") {
        self.progress = current;
        self.progress_total = total;
        self.progress_message = message;
    }

    can reset() {
        self.status = StageStatus.PENDING;
        self.start_time = None;
        self.end_time = None;
        self.input_size = 0;
        self.output_size = 0;
        self.file_count = 0;
        self.files = [];
        self.progress = 0;
        self.progress_total = 0;
        self.progress_message = "";
        self.error_message = None;
    }

    can get_duration() -> float | None {
        if self.start_time is not None and self.end_time is not None {
            return self.end_time - self.start_time;
        }
        return None;
    }

    can get_compression_ratio() -> float | None {
        if self.input_size > 0 and self.output_size > 0 {
            return self.output_size / self.input_size;
        }
        return None;
    }

    can to_dict() -> dict {
        return {
            "name": self.name,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.get_duration(),
            "input_size": self.input_size,
            "output_size": self.output_size,
            "compression_ratio": self.get_compression_ratio(),
            "file_count": self.file_count,
            "files": self.files,
            "progress": self.progress,
            "progress_total": self.progress_total,
            "progress_message": self.progress_message,
            "error": self.error_message
        };
    }
}

edge HasStage {}
