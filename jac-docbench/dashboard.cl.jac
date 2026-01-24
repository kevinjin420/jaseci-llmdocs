"""Main dashboard client component."""

include:jac components.progress_bar;
include:jac components.source_panel;
include:jac components.stage_card;
include:jac components.validation_card;
include:jac components.log_view;
include:jac components.file_editor;

import:py json;

cl Dashboard {
    has page: str = "pipeline";
    has connected: bool = False;
    has running: bool = False;
    has sources: list = [];
    has stages: dict = {
        "fetch": {
            "name": "Fetch & Sanitize",
            "status": "pending",
            "input_size": 0,
            "output_size": 0,
            "files": [],
            "compression_ratio": 1,
            "extra": {}
        },
        "extract": {
            "name": "Deterministic Extract",
            "status": "pending",
            "input_size": 0,
            "output_size": 0,
            "files": [],
            "compression_ratio": 1,
            "extra": {}
        },
        "assemble": {
            "name": "LLM Assembly",
            "status": "pending",
            "input_size": 0,
            "output_size": 0,
            "files": [],
            "compression_ratio": 1,
            "extra": {}
        }
    };
    has progress: dict = {};
    has validation: dict | None = None;
    has logs: list = [];
    has metrics: dict | None = None;
    has ws: object | None = None;

    can :async: :init: {
        await self.fetch_sources();
        await self.fetch_status();
        self.connect_websocket();
    }

    can :async: fetch_sources() {
        try {
            res = await fetch("/api/sources");
            data = await res.json();
            self.sources = data.get("sources", []);
        } except Exception as e {
            print(f"Failed to fetch sources: {e}");
        }
    }

    can :async: add_source(source_data: dict) {
        res = await fetch("/api/sources", {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(source_data)
        });
        if not res.ok {
            err = await res.json();
            raise Exception(err.get("detail", "Failed to add source"));
        }
        await self.fetch_sources();
    }

    can :async: delete_source(id: str) {
        try {
            await fetch(f"/api/sources/{id}", {"method": "DELETE"});
            await self.fetch_sources();
        } except Exception as e {
            print(f"Failed to delete source: {e}");
        }
    }

    can :async: toggle_source(id: str) {
        try {
            await fetch(f"/api/sources/{id}/toggle", {"method": "POST"});
            await self.fetch_sources();
        } except Exception as e {
            print(f"Failed to toggle source: {e}");
        }
    }

    can :async: fetch_status() {
        try {
            status_res = await fetch("/api/status");
            stages_res = await fetch("/api/stages");

            status = await status_res.json();
            stages_data = await stages_res.json();

            self.running = status.get("is_running", False);

            stage_list = stages_data.get("stages", []);
            if len(stage_list) > 0 {
                stage_keys = ["fetch", "extract", "assemble"];
                for (i, s) in enumerate(stage_list) {
                    if i < len(stage_keys) {
                        key = stage_keys[i];
                        self.stages[key] = {**self.stages[key], **s};
                    }
                }
            }
        } except Exception as e {
            print(f"Failed to fetch status: {e}");
        }
    }

    can connect_websocket() {
        try {
            self.ws = WebSocket(f"ws://{window.location.hostname}:4000/ws");

            self.ws.onopen = || {
                self.connected = True;
            };

            self.ws.onclose = || {
                self.connected = False;
                setTimeout(|| self.connect_websocket(), 2000);
            };

            self.ws.onmessage = |e| {
                msg = json.loads(e.data);
                self.handle_message(msg);
            };
        } except Exception as e {
            print(f"WebSocket connection failed: {e}");
        }
    }

    can handle_message(msg: dict) {
        event_type = msg.get("event", "");

        if event_type != "progress" {
            self.logs = [*self.logs[-99:], msg];
        }

        if event_type == "pipeline_start" {
            self.running = True;
            self.validation = None;
            self.progress = {};
        }

        if event_type == "pipeline_complete" {
            self.running = False;
            self.progress = {};
            if msg.get("data") {
                self.metrics = msg["data"];
            }
        }

        if event_type == "pipeline_error" {
            self.running = False;
            self.progress = {};
            if msg.get("data") {
                self.metrics = msg["data"];
            }
        }

        if event_type == "progress" {
            data = msg.get("data", {});
            stage = data.get("stage");
            if stage {
                self.progress[stage] = {
                    "current": data.get("current", 0),
                    "total": data.get("total", 0),
                    "message": data.get("message", "")
                };
            }
        }

        if event_type == "stage_start" {
            data = msg.get("data", {});
            stage = data.get("stage");
            if stage and stage in self.stages {
                self.stages[stage]["status"] = "running";
            }
        }

        if event_type == "stage_complete" {
            data = msg.get("data", {});
            stage = data.get("stage");
            if stage and stage in self.stages {
                self.stages[stage] = {**self.stages[stage], **data.get("metrics", {}), "status": "complete"};
                if stage in self.progress {
                    del self.progress[stage];
                }
                if data.get("validation") {
                    self.validation = data["validation"];
                }
            }
        }

        if event_type == "stage_error" {
            data = msg.get("data", {});
            stage = data.get("stage");
            if stage and stage in self.stages {
                self.stages[stage]["status"] = "error";
                self.stages[stage]["error"] = data.get("error");
            }
        }
    }

    can :async: run_pipeline() {
        self.logs = [];
        self.stages = {
            "fetch": {"name": "Fetch & Sanitize", "status": "pending", "input_size": 0, "output_size": 0, "files": [], "compression_ratio": 1, "extra": {}},
            "extract": {"name": "Deterministic Extract", "status": "pending", "input_size": 0, "output_size": 0, "files": [], "compression_ratio": 1, "extra": {}},
            "assemble": {"name": "LLM Assembly", "status": "pending", "input_size": 0, "output_size": 0, "files": [], "compression_ratio": 1, "extra": {}}
        };
        self.validation = None;
        self.metrics = None;
        self.progress = {};

        try {
            await fetch("/api/run", {"method": "POST"});
        } except Exception as e {
            print(f"Run pipeline error: {e}");
        }
    }

    can :async: run_stage(stage_key: str) {
        try {
            await fetch(f"/api/run/{stage_key}", {"method": "POST"});
        } except Exception as e {
            print(f"Run stage error: {e}");
        }
    }

    can render() {
        total_input = self.stages["fetch"].get("input_size", 0);
        total_output = self.stages["assemble"].get("output_size", 0);
        overall_ratio = total_output / total_input if total_input > 0 else 0;

        <div class="min-h-screen bg-zinc-950 text-white p-6">
            <div class="max-w-6xl mx-auto">
                {self.render_header()}

                {self.page == "config" and (
                    <div class="flex flex-col" style="height: calc(100vh - 120px)">
                        <SourcePanel
                            sources={self.sources}
                            on_add={self.add_source}
                            on_delete={self.delete_source}
                            on_toggle={self.toggle_source}
                            on_refresh={self.fetch_sources}
                        />
                        <FileEditor />
                    </div>
                )}

                {self.page == "pipeline" and (
                    <>
                        {self.render_metrics(total_input, total_output, overall_ratio)}
                        {self.render_stages()}
                        {self.render_bottom_section()}
                    </>
                )}
            </div>
        </div>;
    }

    can render_header() {
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-6">
                <div>
                    <h1 class="text-2xl font-bold">Pipeline Dashboard</h1>
                    <p class="text-zinc-500 text-sm">Documentation compression pipeline</p>
                </div>
                <div class="flex gap-1 bg-zinc-900 rounded-lg p-1">
                    <button
                        onclick={|| self.page = "pipeline"}
                        class={f"px-4 py-1.5 text-sm rounded-md transition {
                            'bg-zinc-700 text-white' if self.page == 'pipeline' else 'text-zinc-400 hover:text-white'
                        }"}
                    >
                        Pipeline
                    </button>
                    <button
                        onclick={|| self.page = "config"}
                        class={f"px-4 py-1.5 text-sm rounded-md transition {
                            'bg-zinc-700 text-white' if self.page == 'config' else 'text-zinc-400 hover:text-white'
                        }"}
                    >
                        Config
                    </button>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <div class={f"w-2 h-2 rounded-full {'bg-green-500' if self.connected else 'bg-red-500'}"} />
                <span class="text-sm text-zinc-400">
                    {"Connected" if self.connected else "Disconnected"}
                </span>
                {self.page == "pipeline" and (
                    <button
                        onclick={self.run_pipeline}
                        disabled={self.running or not self.connected}
                        class={f"px-4 py-2 rounded font-medium transition {
                            'bg-zinc-700 text-zinc-400 cursor-not-allowed' if self.running or not self.connected
                            else 'bg-blue-600 hover:bg-blue-500 text-white'
                        }"}
                    >
                        {"Running..." if self.running else "Run Pipeline"}
                    </button>
                )}
            </div>
        </div>;
    }

    can render_metrics(total_input: int, total_output: int, overall_ratio: float) {
        <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
                <div class="text-zinc-500 text-sm">Total Input</div>
                <div class="text-xl font-bold">
                    {format_bytes(total_input) if total_input > 0 else "-"}
                </div>
            </div>
            <div class="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
                <div class="text-zinc-500 text-sm">Total Output</div>
                <div class="text-xl font-bold">
                    {format_bytes(total_output) if total_output > 0 else "-"}
                </div>
            </div>
            <div class="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
                <div class="text-zinc-500 text-sm">Compression</div>
                <div class={f"text-xl font-bold {'text-green-400' if overall_ratio > 0 and overall_ratio < 0.05 else ''}"}>
                    {f"{overall_ratio * 100:.2f}%" if overall_ratio > 0 else "-"}
                </div>
            </div>
            <div class="p-4 bg-zinc-900 rounded-lg border border-zinc-800">
                <div class="text-zinc-500 text-sm">Duration</div>
                <div class="text-xl font-bold">
                    {format_duration(self.metrics.get("total_duration")) if self.metrics else "-"}
                </div>
            </div>
        </div>;
    }

    can render_stages() {
        active_stage = None;
        for (key, stage) in self.stages.items() {
            if stage.get("status") == "running" {
                active_stage = key;
                break;
            }
        }

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {[
                <StageCard
                    key={key}
                    stage_key={key}
                    stage={stage}
                    is_active={active_stage == key}
                    progress={self.progress.get(key)}
                    on_run={self.run_stage}
                    disabled={self.running or not self.connected}
                />
                for (key, stage) in self.stages.items()
            ]}
        </div>;
    }

    can render_bottom_section() {
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ValidationCard validation={self.validation} />
            <LogView logs={self.logs} />
        </div>;
    }
}

with entry {
    <Dashboard />;
}
