"""Source node and edge definitions for documentation sources."""

import:py from uuid import uuid4;

enum SourceType {
    DOCS = "docs",
    JAC = "jac",
    BOTH = "both"
}

node Source {
    has id: str = str(uuid4());
    has git_url: str;
    has branch: str = "main";
    has path: str = ".";
    has source_type: SourceType = SourceType.DOCS;
    has enabled: bool = True;
    has file_patterns: str | None = None;

    can to_dict() -> dict {
        return {
            "id": self.id,
            "git_url": self.git_url,
            "branch": self.branch,
            "path": self.path,
            "source_type": self.source_type.value,
            "enabled": self.enabled,
            "file_patterns": self.file_patterns
        };
    }

    can update_from(data: dict) {
        if "git_url" in data {
            self.git_url = data["git_url"];
        }
        if "branch" in data {
            self.branch = data["branch"];
        }
        if "path" in data {
            self.path = data["path"];
        }
        if "source_type" in data {
            self.source_type = SourceType(data["source_type"]);
        }
        if "enabled" in data {
            self.enabled = data["enabled"];
        }
        if "file_patterns" in data {
            self.file_patterns = data["file_patterns"];
        }
    }
}

edge HasSource {}
