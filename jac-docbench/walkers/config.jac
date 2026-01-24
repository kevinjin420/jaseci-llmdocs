"""Configuration and prompts walker endpoints."""

include:jac config;

import:py from pathlib import Path;

walker get_config {
    """GET /api/config - Get current configuration."""

    has __specs__: dict = {
        "path": "/api/config",
        "methods": ["GET"]
    };

    can enter with `root entry {
        report {"config": config.to_dict()};
    }
}

walker update_config {
    """PUT /api/config - Update configuration."""

    has __specs__: dict = {
        "path": "/api/config",
        "methods": ["PUT"]
    };

    has config_data: dict;

    can enter with `root entry {
        config.update_from(self.config_data);
        config.save();
        report {"config": config.to_dict(), "message": "Configuration updated"};
    }
}

walker list_prompts {
    """GET /api/prompts - List all prompt files."""

    has __specs__: dict = {
        "path": "/api/prompts",
        "methods": ["GET"]
    };

    can enter with `root entry {
        prompts_dir = Path(PROMPTS_DIR);
        prompt_files = [];
        if prompts_dir.exists() {
            for f in prompts_dir.glob("*.txt") {
                prompt_files.append({
                    "filename": f.name,
                    "path": str(f),
                    "size": f.stat().st_size
                });
            }
        }
        report {"prompts": prompt_files};
    }
}

walker get_prompt {
    """GET /api/prompts/{filename} - Get prompt content."""

    has __specs__: dict = {
        "path": "/api/prompts/{filename}",
        "methods": ["GET"]
    };

    has filename: str;

    can enter with `root entry {
        content = load_prompt(self.filename);
        if content is not None {
            report {
                "filename": self.filename,
                "content": content
            };
        } else {
            report {"error": "Prompt file not found", "status": 404};
        }
    }
}

walker update_prompt {
    """PUT /api/prompts/{filename} - Update prompt content."""

    has __specs__: dict = {
        "path": "/api/prompts/{filename}",
        "methods": ["PUT"]
    };

    has filename: str;
    has content: str;

    can enter with `root entry {
        if save_prompt(self.filename, self.content) {
            report {
                "filename": self.filename,
                "message": "Prompt updated",
                "size": len(self.content)
            };
        } else {
            report {"error": "Failed to save prompt", "status": 500};
        }
    }
}
