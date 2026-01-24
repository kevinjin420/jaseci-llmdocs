"""Source management walker endpoints."""

include:jac models.source;

import:py from uuid import uuid4;

obj SourceCreate {
    has git_url: str;
    has branch: str = "main";
    has path: str = ".";
    has source_type: str = "docs";
    has file_patterns: str | None = None;
}

obj SourceUpdate {
    has git_url: str | None = None;
    has branch: str | None = None;
    has path: str | None = None;
    has source_type: str | None = None;
    has enabled: bool | None = None;
    has file_patterns: str | None = None;
}

walker list_sources {
    """GET /api/sources - List all sources."""

    has __specs__: dict = {
        "path": "/api/sources",
        "methods": ["GET"]
    };

    can enter with `root entry {
        sources = [];
        for edge in here._jac_.edges {
            if isinstance(edge, HasSource) {
                target = edge._jac_.target;
                if isinstance(target, Source) {
                    sources.append(target.to_dict());
                }
            }
        }
        report {"sources": sources};
    }
}

walker get_source {
    """GET /api/sources/{id} - Get a source by ID."""

    has __specs__: dict = {
        "path": "/api/sources/{source_id}",
        "methods": ["GET"]
    };

    has source_id: str;

    can enter with `root entry {
        for edge in here._jac_.edges {
            if isinstance(edge, HasSource) {
                target = edge._jac_.target;
                if isinstance(target, Source) and target.id == self.source_id {
                    report target.to_dict();
                    disengage;
                }
            }
        }
        report {"error": "Source not found", "status": 404};
    }
}

walker create_source {
    """POST /api/sources - Create a new source."""

    has __specs__: dict = {
        "path": "/api/sources",
        "methods": ["POST"]
    };

    has git_url: str;
    has branch: str = "main";
    has path: str = ".";
    has source_type: str = "docs";
    has file_patterns: str | None = None;

    can enter with `root entry {
        source = Source(
            id=str(uuid4()),
            git_url=self.git_url,
            branch=self.branch,
            path=self.path,
            source_type=SourceType(self.source_type),
            enabled=True,
            file_patterns=self.file_patterns
        );
        here ++> HasSource() ++> source;
        report {"source": source.to_dict(), "message": "Source created"};
    }
}

walker update_source {
    """PUT /api/sources/{id} - Update a source."""

    has __specs__: dict = {
        "path": "/api/sources/{source_id}",
        "methods": ["PUT"]
    };

    has source_id: str;
    has git_url: str | None = None;
    has branch: str | None = None;
    has path: str | None = None;
    has source_type: str | None = None;
    has enabled: bool | None = None;
    has file_patterns: str | None = None;

    can enter with `root entry {
        for edge in here._jac_.edges {
            if isinstance(edge, HasSource) {
                target = edge._jac_.target;
                if isinstance(target, Source) and target.id == self.source_id {
                    update_data = {};
                    if self.git_url is not None {
                        update_data["git_url"] = self.git_url;
                    }
                    if self.branch is not None {
                        update_data["branch"] = self.branch;
                    }
                    if self.path is not None {
                        update_data["path"] = self.path;
                    }
                    if self.source_type is not None {
                        update_data["source_type"] = self.source_type;
                    }
                    if self.enabled is not None {
                        update_data["enabled"] = self.enabled;
                    }
                    if self.file_patterns is not None {
                        update_data["file_patterns"] = self.file_patterns;
                    }
                    target.update_from(update_data);
                    report {"source": target.to_dict(), "message": "Source updated"};
                    disengage;
                }
            }
        }
        report {"error": "Source not found", "status": 404};
    }
}

walker delete_source {
    """DELETE /api/sources/{id} - Delete a source."""

    has __specs__: dict = {
        "path": "/api/sources/{source_id}",
        "methods": ["DELETE"]
    };

    has source_id: str;

    can enter with `root entry {
        for edge in here._jac_.edges {
            if isinstance(edge, HasSource) {
                target = edge._jac_.target;
                if isinstance(target, Source) and target.id == self.source_id {
                    del edge;
                    report {"message": "Source deleted", "id": self.source_id};
                    disengage;
                }
            }
        }
        report {"error": "Source not found", "status": 404};
    }
}

walker toggle_source {
    """POST /api/sources/{id}/toggle - Toggle source enabled status."""

    has __specs__: dict = {
        "path": "/api/sources/{source_id}/toggle",
        "methods": ["POST"]
    };

    has source_id: str;

    can enter with `root entry {
        for edge in here._jac_.edges {
            if isinstance(edge, HasSource) {
                target = edge._jac_.target;
                if isinstance(target, Source) and target.id == self.source_id {
                    target.enabled = not target.enabled;
                    report {
                        "source": target.to_dict(),
                        "message": f"Source {'enabled' if target.enabled else 'disabled'}"
                    };
                    disengage;
                }
            }
        }
        report {"error": "Source not found", "status": 404};
    }
}
