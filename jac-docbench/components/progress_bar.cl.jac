"""Progress bar component for real-time progress display."""

can format_bytes(bytes: int) -> str {
    if bytes == 0 {
        return "0 B";
    }
    k = 1024;
    sizes = ["B", "KB", "MB"];
    i = int(log(bytes) / log(k));
    return f"{bytes / (k ** i):.1f} {sizes[i]}";
}

can format_duration(seconds: float | None) -> str {
    if seconds is None {
        return "-";
    }
    if seconds < 60 {
        return f"{seconds:.1f}s";
    }
    return f"{int(seconds // 60)}m {int(seconds % 60)}s";
}

cl ProgressBar {
    has current: int = 0;
    has total: int = 0;
    has message: str = "";

    can render() {
        percent = (self.current / self.total * 100) if self.total > 0 else 0;

        <div class="mt-3">
            <div class="flex justify-between text-xs text-zinc-400 mb-1">
                <span class="truncate max-w-[70%]">
                    {self.message or "Processing..."}
                </span>
                <span>{self.current}/{self.total}</span>
            </div>
            <div class="h-2 bg-zinc-700 rounded-full overflow-hidden">
                <div
                    class="h-full bg-blue-500 transition-all duration-200"
                    style={f"width: {percent}%"}
                />
            </div>
        </div>;
    }
}
