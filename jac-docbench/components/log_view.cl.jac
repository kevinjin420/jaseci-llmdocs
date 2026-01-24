"""Event log view component."""

cl LogEntry {
    has event: dict = {};

    has event_colors: dict = {
        "pipeline_start": "text-blue-400",
        "pipeline_complete": "text-green-400",
        "pipeline_error": "text-red-400",
        "stage_start": "text-cyan-400",
        "stage_complete": "text-green-400",
        "stage_error": "text-red-400",
        "progress": "text-zinc-500"
    };

    can render() {
        event_type = self.event.get("event", "");

        if event_type == "progress" {
            return None;
        }

        timestamp = self.event.get("timestamp");
        import:py from datetime import datetime;

        <div class="text-xs font-mono py-1 border-b border-zinc-800">
            <span class="text-zinc-500">
                {datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else ""}
            </span>
            <span class={f"ml-2 {self.event_colors.get(event_type, 'text-white')}"}>
                {event_type}
            </span>
            {self.event.get("data", {}).get("stage") and (
                <span class="ml-2 text-zinc-400">
                    [{self.event["data"]["stage"]}]
                </span>
            )}
        </div>;
    }
}

cl LogView {
    has logs: list = [];

    can render() {
        <div class="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
            <h3 class="font-medium text-white mb-3">Event Log</h3>
            <div class="h-48 overflow-y-auto bg-zinc-950 rounded p-2">
                {len(self.logs) == 0 ? (
                    <div class="text-zinc-600 text-sm">No events yet</div>
                ) : (
                    [<LogEntry key={i} event={log} /> for (i, log) in enumerate(self.logs)]
                )}
            </div>
        </div>;
    }
}
