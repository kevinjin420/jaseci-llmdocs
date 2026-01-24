"""Tests for deterministic extraction logic."""

include:jac pipeline.extractor;
include:jac utils.patterns;

test test_classify_code_node {
    """Test classifying code with node definition."""
    code = '''
node Person {
    has name: str;
    has age: int;
}
''';

    types = classify_code(code);
    assert "node" in types;
}

test test_classify_code_walker {
    """Test classifying code with walker definition."""
    code = '''
walker greet {
    can say_hello with `root entry {
        print("Hello!");
    }
}
''';

    types = classify_code(code);
    assert "walker" in types;
    assert "with_entry" in types;
}

test test_classify_code_edge_operators {
    """Test classifying code with edge operators."""
    code = '''
node1 ++> node2;
node3 <++> node4;
''';

    types = classify_code(code);
    assert "connect" in types;
}

test test_classify_code_by_llm {
    """Test classifying code with by llm()."""
    code = '''
can summarize(text: str) -> str
by llm(model=openai, temperature=0.5);
''';

    types = classify_code(code);
    assert "by_llm" in types;
}

test test_classify_code_spawn {
    """Test classifying code with spawn."""
    code = '''
spawn MyWalker() on root;
''';

    types = classify_code(code);
    assert "spawn" in types;
}

test test_find_keywords {
    """Test finding critical keywords in code."""
    code = '''
walker graph_traverser {
    can traverse with `root entry {
        visit [-->];
        here ++> new_node;
        spawn SubWalker();
        report self.results;
    }
}
''';

    keywords = find_keywords(code);
    assert "++>" in keywords;
    assert "-->" in keywords;
    assert "spawn" in keywords;
    assert "visit" in keywords;
    assert "report" in keywords;
    assert "here" in keywords;
    assert "self" in keywords;
}

test test_find_patterns {
    """Test finding critical patterns in text."""
    text = '''
node MyNode {
    has value: int;
}

walker MyWalker {
    can walk with entry {
        visit [-->];
        spawn SubWalker();
    }
}

can process() by llm();
''';

    patterns = find_patterns(text);
    assert "node definition" in patterns;
    assert "walker definition" in patterns;
    assert "with entry" in patterns;
    assert "spawn" in patterns;
    assert "has x: type" in patterns;
    assert "by llm()" in patterns;
}

test test_validate_code_blocks_balanced {
    """Test validation of balanced code blocks."""
    text = '''
```jac
node Test {}
```

Some text

```python
print("hello")
```
''';

    (valid, error) = validate_code_blocks(text);
    assert valid == True;
    assert error is None;
}

test test_validate_code_blocks_unbalanced {
    """Test validation of unbalanced code blocks."""
    text = '''
```jac
node Test {}

Some text without closing fence
''';

    (valid, error) = validate_code_blocks(text);
    assert valid == False;
    assert error == "Unbalanced code fences";
}

test test_code_example_creation {
    """Test CodeExample object creation."""
    example = CodeExample(
        code="node Test {\n    has x: int;\n}",
        source_file="test.md",
        construct_type="node",
        has_keywords=["has"]
    );

    assert example.line_count == 3;
    assert example.source_file == "test.md";
    assert example.construct_type == "node";
}

test test_extracted_content_creation {
    """Test ExtractedContent object creation."""
    content = ExtractedContent();

    assert len(content.signatures) == 0;
    assert len(content.examples) == 0;
    assert len(content.keywords_found) == 0;
    assert content.total_examples == 0;
    assert content.total_signatures == 0;
}

test test_extractor_classify_code {
    """Test DeterministicExtractor code classification."""
    extractor = DeterministicExtractor();

    code = '''
async walker api_handler {
    has __specs__: dict = {"path": "/api", "methods": ["GET"]};

    can handle with `root entry {
        report {"status": "ok"};
    }
}
''';

    types = classify_code(code);
    assert "walker" in types;
    assert "async" in types;
    assert "__specs__" in types;
    assert "with_entry" in types;
    assert "report" in types;
}

test test_should_exclude_patterns {
    """Test path exclusion patterns."""
    import:py from pathlib import Path;

    excluded_paths = [
        Path("docs/internals/core.md"),
        Path("docs/playground/test.md"),
        Path("docs/contributing/guide.md"),
        Path("README.md"),
        Path("index.md")
    ];

    for path in excluded_paths {
        result = should_exclude(path);
        assert result == True, f"Expected {path} to be excluded";
    }

    included_paths = [
        Path("docs/tutorial/basics.md"),
        Path("docs/reference/nodes.md"),
        Path("examples/hello.jac")
    ];

    for path in included_paths {
        result = should_exclude(path);
        assert result == False, f"Expected {path} to be included";
    }
}
