"""File editor component with Monaco editor wrapper."""

cl FileEditor {
    has files: list = [];
    has selected_file: dict | None = None;
    has content: str = "";
    has original_content: str = "";
    has saving: bool = False;
    has error: str | None = None;
    has modified_files: set = set();

    can :async: fetch_files() {
        try {
            config_res = await fetch("/api/config");
            prompts_res = await fetch("/api/prompts");

            config_data = await config_res.json();
            prompts_data = await prompts_res.json();

            prompts_list = prompts_data.get("prompts", []);
            file_list = [
                {"name": "config.yaml", "type": "config", "language": "yaml"}
            ];

            for p in prompts_list {
                file_list.append({
                    "name": p.get("filename", ""),
                    "type": "prompt",
                    "language": "plaintext"
                });
            }

            file_list.sort(key=|f| (0 if f["type"] == "config" else 1, f["name"]));
            self.files = file_list;

            if len(file_list) > 0 and self.selected_file is None {
                await self.load_file(file_list[0]);
            }
        } except Exception {
            self.error = "Failed to load files";
        }
    }

    can :async: load_file(file: dict) {
        try {
            if file["type"] == "config" {
                res = await fetch("/api/config");
            } else {
                res = await fetch(f"/api/prompts/{file['name']}");
            }
            data = await res.json();
            self.content = data.get("content", "");
            self.original_content = self.content;
            self.selected_file = file;
            self.error = None;
        } except Exception {
            self.error = "Failed to load file";
        }
    }

    can :async: save_file() {
        if self.selected_file is None {
            return;
        }

        self.saving = True;
        self.error = None;

        try {
            if self.selected_file["type"] == "config" {
                res = await fetch("/api/config", {
                    "method": "PUT",
                    "headers": {"Content-Type": "application/json"},
                    "body": JSON.stringify({"content": self.content})
                });
            } else {
                res = await fetch(f"/api/prompts/{self.selected_file['name']}", {
                    "method": "PUT",
                    "headers": {"Content-Type": "application/json"},
                    "body": JSON.stringify({"content": self.content})
                });
            }

            if not res.ok {
                err = await res.json();
                raise Exception(err.get("detail", "Save failed"));
            }

            self.original_content = self.content;
            self.modified_files.discard(self.selected_file["name"]);
        } except Exception as e {
            self.error = str(e);
        } finally {
            self.saving = False;
        }
    }

    can handle_editor_change(value: str) {
        self.content = value or "";

        if self.selected_file is not None {
            is_modified = self.content != self.original_content;
            if is_modified {
                self.modified_files.add(self.selected_file["name"]);
            } else {
                self.modified_files.discard(self.selected_file["name"]);
            }
        }
    }

    can render() {
        <div class="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden flex-1 min-h-0">
            <div class="flex h-full">
                <div class="w-48 border-r border-zinc-800 bg-zinc-950 overflow-y-auto">
                    <div class="p-2 text-xs text-zinc-500 uppercase tracking-wide border-b border-zinc-800">
                        Files
                    </div>
                    {[self.render_file_button(file) for file in self.files]}
                </div>

                <div class="flex-1 flex flex-col">
                    <div class="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900">
                        <div class="flex items-center gap-3">
                            <span class="text-sm text-white">
                                {self.selected_file["name"] if self.selected_file else "No file selected"}
                            </span>
                            {self.saving and <span class="text-xs text-zinc-400">Saving...</span>}
                        </div>
                        {self.error and <span class="text-xs text-red-400">{self.error}</span>}
                    </div>

                    <div class="flex-1">
                        {self.selected_file and (
                            <textarea
                                class="w-full h-full bg-zinc-950 text-white font-mono text-sm p-4 resize-none focus:outline-none"
                                value={self.content}
                                oninput={|e| self.handle_editor_change(e.target.value)}
                                spellcheck={False}
                            />
                        )}
                    </div>
                </div>
            </div>
        </div>;
    }

    can render_file_button(file: dict) {
        is_selected = self.selected_file is not None and self.selected_file["name"] == file["name"];
        is_modified = file["name"] in self.modified_files;

        <button
            key={file["name"]}
            onclick={|| self.load_file(file)}
            class={f"w-full px-3 py-2 text-left text-sm truncate flex items-center gap-2 transition {
                'bg-zinc-800 text-white' if is_selected else 'text-zinc-400 hover:bg-zinc-800 hover:text-white'
            }"}
        >
            <span class="flex-1 truncate">{file["name"]}</span>
            {is_modified and (
                <span class="w-2 h-2 rounded-full bg-yellow-500 flex-shrink-0" />
            )}
        </button>;
    }
}
