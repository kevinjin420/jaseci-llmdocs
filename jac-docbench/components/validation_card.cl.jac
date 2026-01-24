"""Validation results display component."""

cl ValidationCard {
    has validation: dict | None = None;

    can render() {
        if self.validation is None {
            return None;
        }

        is_valid = self.validation.get("is_valid", False);

        <div class={f"p-4 rounded-lg border {
            'border-green-600 bg-green-900/20' if is_valid else 'border-yellow-600 bg-yellow-900/20'
        }"}>
            <h3 class="font-medium text-white mb-3">Validation</h3>
            <div class="grid grid-cols-2 gap-2 text-sm">
                <div class="text-zinc-400">Status:</div>
                <div class={f"{'text-green-400' if is_valid else 'text-yellow-400'}"}>
                    {"PASSED" if is_valid else "WARNINGS"}
                </div>
                <div class="text-zinc-400">Patterns:</div>
                <div class="text-white">
                    {self.validation.get("patterns_found", 0)}/{self.validation.get("patterns_total", 0)}
                </div>
            </div>
            {self.render_missing_patterns()}
            {self.render_issues()}
        </div>;
    }

    can render_missing_patterns() {
        missing = self.validation.get("missing_patterns", []);
        if len(missing) == 0 {
            return None;
        }

        <div class="mt-2 text-xs text-yellow-400">
            Missing: {", ".join(missing)}
        </div>;
    }

    can render_issues() {
        issues = self.validation.get("issues", []);
        if len(issues) == 0 {
            return None;
        }

        <div class="mt-2 text-xs text-yellow-400">
            {", ".join(issues)}
        </div>;
    }
}
