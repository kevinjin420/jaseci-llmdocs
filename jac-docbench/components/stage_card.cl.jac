"""Stage card component for pipeline stage display."""

include:jac components.progress_bar;

cl StageCard {
    has stage: dict = {};
    has stage_key: str = "";
    has is_active: bool = False;
    has progress: dict | None = None;
    has on_run: callable | None = None;
    has disabled: bool = False;

    has stage_descriptions: dict = {
        "fetch": "Fetches docs from git sources, cleans markdown, extracts Jac skeletons",
        "extract": "Categorizes code examples, selects best examples per construct (no LLM)",
        "assemble": "Single LLM call to generate final reference document"
    };

    has status_colors: dict = {
        "pending": "bg-zinc-700",
        "running": "bg-blue-600 animate-pulse",
        "complete": "bg-green-600",
        "error": "bg-red-600"
    };

    can render() {
        status = self.stage.get("status", "pending");
        show_progress = status == "running" and self.progress is not None and self.progress.get("total", 0) > 0;

        <div class={f"rounded-lg border {'border-blue-500 bg-zinc-800' if self.is_active else 'border-zinc-700 bg-zinc-900'}"}>
            <button
                onclick={|| self.on_run(self.stage_key) if self.on_run else None}
                disabled={self.disabled}
                class={f"w-full px-3 py-2 text-xs font-medium rounded-t-lg border-b border-zinc-700 transition {
                    'bg-zinc-800 text-zinc-500 cursor-not-allowed' if self.disabled
                    else 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700 hover:text-white cursor-pointer'
                }"}
            >
                Run Stage
            </button>
            <div class="p-4">
                <div class="mb-3">
                    <h3 class="font-medium text-white">
                        {self.stage.get("name", self.stage_key)}
                    </h3>
                    <p class="text-xs text-zinc-500 mt-1">
                        {self.stage_descriptions.get(self.stage_key, "")}
                    </p>
                    <span class={f"inline-block mt-2 px-2 py-0.5 rounded text-xs text-white {self.status_colors.get(status, 'bg-zinc-700')}"}>
                        {status}
                    </span>
                </div>

                {show_progress ? (
                    <ProgressBar
                        current={self.progress.get("current", 0)}
                        total={self.progress.get("total", 0)}
                        message={self.progress.get("message", "")}
                    />
                ) : (
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        <div class="text-zinc-400">Input:</div>
                        <div class="text-white">
                            {format_bytes(self.stage.get("input_size", 0))}
                        </div>

                        <div class="text-zinc-400">Output:</div>
                        <div class="text-white">
                            {format_bytes(self.stage.get("output_size", 0))}
                        </div>

                        <div class="text-zinc-400">Ratio:</div>
                        <div class={f"{'text-green-400' if self.stage.get('compression_ratio', 1) < 0.5 else 'text-white'}"}>
                            {f"{self.stage.get('compression_ratio', 1) * 100:.0f}%" if self.stage.get("input_size", 0) > 0 else "-"}
                        </div>

                        <div class="text-zinc-400">Duration:</div>
                        <div class="text-white">
                            {format_duration(self.stage.get("duration"))}
                        </div>

                        <div class="text-zinc-400">Files:</div>
                        <div class="text-white">
                            {self.stage.get("file_count", 0) or len(self.stage.get("files", []))}
                        </div>
                    </div>
                )}

                {self.render_files()}
                {self.render_error()}
            </div>
        </div>;
    }

    can render_files() {
        files = self.stage.get("files", []);
        if len(files) == 0 or self.stage.get("status") != "complete" {
            return None;
        }

        <details class="mt-3">
            <summary class="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300">
                View files ({len(files)})
            </summary>
            <div class="mt-2 max-h-32 overflow-y-auto text-xs">
                {[
                    <div key={i} class="flex justify-between text-zinc-400 py-0.5">
                        <span class="truncate mr-2">{f.get("name", "")}</span>
                        <span>{format_bytes(f.get("size", 0))}</span>
                    </div>
                    for (i, f) in enumerate(files[:10])
                ]}
                {len(files) > 10 and (
                    <div class="text-zinc-500">
                        ...and {len(files) - 10} more
                    </div>
                )}
            </div>
        </details>;
    }

    can render_error() {
        error = self.stage.get("error");
        if error is None {
            return None;
        }

        <div class="mt-2 p-2 bg-red-900/50 rounded text-xs text-red-300">
            {error}
        </div>;
    }
}
