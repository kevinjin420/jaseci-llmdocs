"""Tests for source CRUD operations."""

include:jac models.source;
include:jac main;

import:py from uuid import uuid4;

test test_source_creation {
    """Test creating a source node with default values."""
    source = Source(
        id="test-source",
        git_url="https://github.com/example/repo.git"
    );

    assert source.id == "test-source";
    assert source.git_url == "https://github.com/example/repo.git";
    assert source.branch == "main";
    assert source.path == ".";
    assert source.source_type == SourceType.DOCS;
    assert source.enabled == True;
    assert source.file_patterns is None;
}

test test_source_with_custom_values {
    """Test creating a source with custom values."""
    source = Source(
        id="custom-source",
        git_url="https://github.com/example/repo.git",
        branch="develop",
        path="docs/api",
        source_type=SourceType.BOTH,
        enabled=False,
        file_patterns="*.md,*.jac"
    );

    assert source.branch == "develop";
    assert source.path == "docs/api";
    assert source.source_type == SourceType.BOTH;
    assert source.enabled == False;
    assert source.file_patterns == "*.md,*.jac";
}

test test_source_to_dict {
    """Test source serialization to dictionary."""
    source = Source(
        id="dict-test",
        git_url="https://github.com/test/repo.git",
        source_type=SourceType.JAC
    );

    d = source.to_dict();

    assert d["id"] == "dict-test";
    assert d["git_url"] == "https://github.com/test/repo.git";
    assert d["source_type"] == "jac";
    assert d["enabled"] == True;
}

test test_source_update_from {
    """Test updating source from dictionary."""
    source = Source(
        id="update-test",
        git_url="https://github.com/original/repo.git"
    );

    source.update_from({
        "branch": "feature",
        "enabled": False,
        "source_type": "both"
    });

    assert source.branch == "feature";
    assert source.enabled == False;
    assert source.source_type == SourceType.BOTH;
    assert source.git_url == "https://github.com/original/repo.git";
}

test test_source_type_enum {
    """Test SourceType enum values."""
    assert SourceType.DOCS.value == "docs";
    assert SourceType.JAC.value == "jac";
    assert SourceType.BOTH.value == "both";

    assert SourceType("docs") == SourceType.DOCS;
    assert SourceType("jac") == SourceType.JAC;
    assert SourceType("both") == SourceType.BOTH;
}

test test_graph_initialization {
    """Test root graph initialization."""
    root = initialize_graph();

    assert root is not None;
    assert root.initialized == True;
    assert root.created_at is not None;
}

test test_add_source_to_graph {
    """Test adding a source to the root graph."""
    root = initialize_graph();

    source = Source(
        id="graph-source",
        git_url="https://github.com/graph/test.git"
    );

    add_source(source);

    sources = get_sources();
    found = False;
    for s in sources {
        if s.id == "graph-source" {
            found = True;
            break;
        }
    }

    assert found == True;
}

test test_find_source {
    """Test finding a source by ID."""
    root = initialize_graph();

    source = Source(
        id="findable-source",
        git_url="https://github.com/find/me.git"
    );

    add_source(source);

    found = find_source("findable-source");
    assert found is not None;
    assert found.id == "findable-source";

    not_found = find_source("nonexistent");
    assert not_found is None;
}

test test_remove_source {
    """Test removing a source from the graph."""
    root = initialize_graph();

    source = Source(
        id="removable-source",
        git_url="https://github.com/remove/me.git"
    );

    add_source(source);

    removed = remove_source("removable-source");
    assert removed == True;

    found = find_source("removable-source");
    assert found is None;

    not_removed = remove_source("nonexistent");
    assert not_removed == False;
}
