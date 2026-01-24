"""Source management UI panel."""

cl SourcePanel {
    has sources: list = [];
    has on_add: callable | None = None;
    has on_delete: callable | None = None;
    has on_toggle: callable | None = None;
    has on_refresh: callable | None = None;

    has expanded: bool = False;
    has show_form: bool = False;
    has form_data: dict = {
        "id": "",
        "git_url": "",
        "branch": "main",
        "path": ".",
        "source_type": "docs"
    };
    has error: str | None = None;

    can handle_submit(e: object) {
        e.preventDefault();
        self.error = None;

        if not self.form_data["id"] or not self.form_data["git_url"] {
            self.error = "ID and Git URL are required";
            return;
        }

        try {
            if self.on_add is not None {
                self.on_add(self.form_data);
            }
            self.form_data = {
                "id": "",
                "git_url": "",
                "branch": "main",
                "path": ".",
                "source_type": "docs"
            };
            self.show_form = False;
        } except Exception as err {
            self.error = str(err);
        }
    }

    can get_type_label(source_type: str) -> str {
        labels = {
            "docs": "Documentation",
            "jac": "Jac Code",
            "both": "Both"
        };
        return labels.get(source_type, source_type);
    }

    can get_type_class(source_type: str) -> str {
        classes = {
            "docs": "bg-blue-900 text-blue-300",
            "jac": "bg-purple-900 text-purple-300",
            "both": "bg-cyan-900 text-cyan-300"
        };
        return classes.get(source_type, "");
    }

    can render() {
        enabled_count = len([s for s in self.sources if s.get("enabled", True)]);

        <div class="bg-zinc-900 rounded-lg border border-zinc-800 mb-6">
            <button
                onclick={|| self.expanded = not self.expanded}
                class="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-zinc-800 rounded-lg transition"
            >
                <div class="flex items-center gap-3">
                    <span class={f"text-zinc-400 text-xs transition-transform {'rotate-90' if self.expanded else ''}"}>
                        &gt;
                    </span>
                    <h3 class="font-medium text-white">Sources</h3>
                    <span class="text-xs text-zinc-500">({enabled_count} enabled)</span>
                </div>
                <div class="flex gap-2" onclick={|e| e.stopPropagation()}>
                    <button
                        onclick={|| self.on_refresh() if self.on_refresh else None}
                        class="px-3 py-1 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded transition"
                    >
                        Refresh
                    </button>
                    <button
                        onclick={|| { self.show_form = not self.show_form; self.expanded = True; }}
                        class="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition"
                    >
                        {"Cancel" if self.show_form else "Add"}
                    </button>
                </div>
            </button>

            {self.expanded and <div class="px-4 pb-4">
                {self.show_form and (
                    <form onsubmit={self.handle_submit} class="mb-4 p-3 bg-zinc-800 rounded-lg">
                        {self.error and (
                            <div class="mb-3 p-2 bg-red-900/50 text-red-300 text-xs rounded">
                                {self.error}
                            </div>
                        )}
                        <div class="grid grid-cols-2 gap-3">
                            <div class="col-span-2">
                                <label class="block text-xs text-zinc-400 mb-1">ID</label>
                                <input
                                    type="text"
                                    value={self.form_data["id"]}
                                    oninput={|e| self.form_data["id"] = e.target.value}
                                    placeholder="my-source"
                                    class="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
                                />
                            </div>
                            <div class="col-span-2">
                                <label class="block text-xs text-zinc-400 mb-1">Git URL</label>
                                <input
                                    type="text"
                                    value={self.form_data["git_url"]}
                                    oninput={|e| self.form_data["git_url"] = e.target.value}
                                    placeholder="https://github.com/user/repo.git"
                                    class="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
                                />
                            </div>
                            <div>
                                <label class="block text-xs text-zinc-400 mb-1">Branch</label>
                                <input
                                    type="text"
                                    value={self.form_data["branch"]}
                                    oninput={|e| self.form_data["branch"] = e.target.value}
                                    placeholder="main"
                                    class="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
                                />
                            </div>
                            <div>
                                <label class="block text-xs text-zinc-400 mb-1">Path</label>
                                <input
                                    type="text"
                                    value={self.form_data["path"]}
                                    oninput={|e| self.form_data["path"] = e.target.value}
                                    placeholder="docs/"
                                    class="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
                                />
                            </div>
                            <div>
                                <label class="block text-xs text-zinc-400 mb-1">Type</label>
                                <select
                                    value={self.form_data["source_type"]}
                                    onchange={|e| self.form_data["source_type"] = e.target.value}
                                    class="w-full px-2 py-1 text-sm bg-zinc-900 border border-zinc-700 rounded text-white"
                                >
                                    <option value="docs">Documentation (.md)</option>
                                    <option value="jac">Jac Code (.jac)</option>
                                    <option value="both">Both</option>
                                </select>
                            </div>
                            <div class="flex items-end">
                                <button
                                    type="submit"
                                    class="w-full px-3 py-1 text-sm bg-green-600 hover:bg-green-500 text-white rounded transition"
                                >
                                    Add Source
                                </button>
                            </div>
                        </div>
                    </form>
                )}

                <div class="space-y-2">
                    {len(self.sources) == 0 ? (
                        <div class="text-zinc-500 text-sm py-4 text-center">
                            No sources configured
                        </div>
                    ) : (
                        [self.render_source(source) for source in self.sources]
                    )}
                </div>
            </div>}
        </div>;
    }

    can render_source(source: dict) {
        enabled = source.get("enabled", True);

        <div
            key={source["id"]}
            class={f"flex items-center justify-between p-3 rounded-lg border {
                'bg-zinc-800 border-zinc-700' if enabled else 'bg-zinc-900 border-zinc-800 opacity-60'
            }"}
        >
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span class="font-medium text-white truncate">{source["id"]}</span>
                    <span class={f"px-1.5 py-0.5 text-xs rounded {self.get_type_class(source.get('source_type', 'docs'))}"}>
                        {self.get_type_label(source.get("source_type", "docs"))}
                    </span>
                </div>
                <div class="text-xs text-zinc-500 truncate mt-1">
                    {source["git_url"]} ({source.get("branch", "main")}:{source.get("path", ".")})
                </div>
            </div>
            <div class="flex items-center gap-2 ml-3">
                <button
                    onclick={|| self.on_toggle(source["id"]) if self.on_toggle else None}
                    class={f"px-2 py-1 text-xs rounded transition {
                        'bg-green-900 text-green-300 hover:bg-green-800' if enabled
                        else 'bg-zinc-700 text-zinc-400 hover:bg-zinc-600'
                    }"}
                >
                    {"Enabled" if enabled else "Disabled"}
                </button>
                <button
                    onclick={|| self.on_delete(source["id"]) if self.on_delete else None}
                    class="px-2 py-1 text-xs bg-red-900 text-red-300 hover:bg-red-800 rounded transition"
                >
                    Delete
                </button>
            </div>
        </div>;
    }
}
