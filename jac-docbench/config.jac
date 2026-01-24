"""Configuration management for jac-docbench."""

import:py from pathlib import Path;
import:py yaml;
import:py os;

glob CONFIG_PATH: str = "config/config.yaml";
glob PROMPTS_DIR: str = "config";

obj Config {
    has prompts: dict = {};
    has source_dir: str = "docs";
    has llm: dict = {};
    has processing: dict = {};
    has validation: dict = {};
    has extraction: dict = {};
    has merge: dict = {};
    has hierarchical_merge: dict = {};
    has ultra_compression: dict = {};

    can :init:(config_path: str = CONFIG_PATH) {
        self.load(config_path);
    }

    can load(config_path: str) {
        path = Path(config_path);
        if path.exists() {
            with open(path, 'r') as f {
                data = yaml.safe_load(f);
            }
            self.prompts = data.get("prompts", {});
            self.source_dir = data.get("source_dir", "docs");
            self.llm = data.get("llm", {});
            self.processing = data.get("processing", {});
            self.validation = data.get("validation", {});
            self.extraction = data.get("extraction", {});
            self.merge = data.get("merge", {});
            self.hierarchical_merge = data.get("hierarchical_merge", {});
            self.ultra_compression = data.get("ultra_compression", {});
        }
    }

    can save(config_path: str = CONFIG_PATH) {
        data = {
            "prompts": self.prompts,
            "source_dir": self.source_dir,
            "llm": self.llm,
            "processing": self.processing,
            "validation": self.validation,
            "extraction": self.extraction,
            "merge": self.merge,
            "hierarchical_merge": self.hierarchical_merge,
            "ultra_compression": self.ultra_compression
        };
        with open(config_path, 'w') as f {
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False);
        }
    }

    can to_dict() -> dict {
        return {
            "prompts": self.prompts,
            "source_dir": self.source_dir,
            "llm": self.llm,
            "processing": self.processing,
            "validation": self.validation,
            "extraction": self.extraction,
            "merge": self.merge,
            "hierarchical_merge": self.hierarchical_merge,
            "ultra_compression": self.ultra_compression
        };
    }

    can update_from(data: dict) {
        if "prompts" in data {
            self.prompts = data["prompts"];
        }
        if "source_dir" in data {
            self.source_dir = data["source_dir"];
        }
        if "llm" in data {
            self.llm = data["llm"];
        }
        if "processing" in data {
            self.processing = data["processing"];
        }
        if "validation" in data {
            self.validation = data["validation"];
        }
        if "extraction" in data {
            self.extraction = data["extraction"];
        }
        if "merge" in data {
            self.merge = data["merge"];
        }
        if "hierarchical_merge" in data {
            self.hierarchical_merge = data["hierarchical_merge"];
        }
        if "ultra_compression" in data {
            self.ultra_compression = data["ultra_compression"];
        }
    }

    can get_llm_api_key() -> str | None {
        env_var = self.llm.get("api_key_env", "OPENROUTER_API_KEY");
        return os.environ.get(env_var);
    }

    can get_llm_model() -> str {
        return self.llm.get("model", "anthropic/claude-opus-4.5");
    }

    can get_critical_patterns() -> list[str] {
        return self.validation.get("critical_patterns", []);
    }
}

can load_prompt(filename: str) -> str | None {
    path = Path(PROMPTS_DIR) / filename;
    if path.exists() {
        with open(path, 'r') as f {
            return f.read();
        }
    }
    return None;
}

can save_prompt(filename: str, content: str) -> bool {
    path = Path(PROMPTS_DIR) / filename;
    try {
        with open(path, 'w') as f {
            f.write(content);
        }
        return True;
    } except Exception {
        return False;
    }
}

can list_prompts() -> list[str] {
    path = Path(PROMPTS_DIR);
    if path.exists() {
        return [f.name for f in path.glob("*.txt")];
    }
    return [];
}

glob config: Config = Config();
