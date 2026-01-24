"""Regex patterns for Jac code detection and extraction."""

import:py re;

glob CONSTRUCT_PATTERNS: dict = {
    "node": r"\bnode\s+\w+",
    "edge": r"\bedge\s+\w+",
    "walker": r"\bwalker\s+\w+",
    "obj": r"\bobj\s+\w+",
    "enum": r"\benum\s+\w+",
    "glob": r"\bglob\s+\w+",
    "can": r"\bcan\s+\w+",
    "def": r"\bdef\s+\w+",
    "with_entry": r"with\s+.*?\s+entry",
    "with_exit": r"with\s+.*?\s+exit",
    "by_llm": r"by\s+llm\s*\(",
    "spawn": r"\bspawn\b",
    "visit": r"\bvisit\s+\[",
    "connect": r"\+\+>|<\+\+>|\+>|<\+",
    "traverse": r"\[.*?-->.*?\]|\[.*?<--.*?\]",
    "filter": r"\(\?\w+",
    "report": r"\breport\b",
    "__specs__": r"__specs__",
    "async": r"\basync\s+(walker|def)",
    "websocket": r"websocket",
    "serve": r"jac\s+serve"
};

glob CRITICAL_KEYWORDS: list[str] = [
    "++>", "<++>", "-->", "<-->", "+>", "<+",
    "spawn", "visit", "report", "disengage",
    "here", "self", "visitor", "by llm",
    "with entry", "with exit", "`root"
];

glob CRITICAL_PATTERNS: list[tuple] = [
    (r"\+\+>", "edge: ++>"),
    (r"<\+\+>", "edge: <++>"),
    (r"-->", "edge: -->"),
    (r"<-->", "edge: <-->"),
    (r"by\s+llm\s*\(", "by llm()"),
    (r"with\s+entry", "with entry"),
    (r"with\s+exit", "with exit"),
    (r"`root\s+entry", "root entry"),
    (r"\bspawn\b", "spawn"),
    (r"import:py", "import:py"),
    (r"\bhas\s+\w+\s*:", "has x: type"),
    (r"\bnode\s+\w+", "node definition"),
    (r"\bwalker\s+\w+", "walker definition"),
    (r"\bedge\s+\w+", "edge definition"),
    (r"\bobj\s+\w+", "obj definition"),
    (r"\bcan\s+\w+", "ability definition"),
    (r"file\.open", "file.open"),
    (r"json\.dumps", "json.dumps"),
    (r"json\.loads", "json.loads"),
    (r"\basync\b", "async"),
    (r"\bawait\b", "await"),
    (r"\breport\b", "report"),
    (r"\bvisit\b", "visit"),
    (r"\bhere\b", "here keyword"),
    (r"\bself\b", "self keyword")
];

glob EXCLUDE_PATTERNS: list[str] = [
    "**/release_notes/**",
    "**/breaking_changes.md",
    "**/CHANGELOG.md",
    "**/CONTRIBUTING.md",
    "**/contributing/**",
    "**/internals/**",
    "**/playground/**",
    "**/roadmap.md",
    "**/index.md",
    "**/README.md"
];

glob EXCLUDE_DIRS: set = {"internals", "playground", "communityhub", "contributing"};

can classify_code(code: str) -> list[str] {
    """Classify code block by construct types it demonstrates."""
    types: list[str] = [];
    for (construct, pattern) in CONSTRUCT_PATTERNS.items() {
        if re.search(pattern, code, re.IGNORECASE) {
            types.append(construct);
        }
    }
    return types;
}

can find_keywords(code: str) -> list[str] {
    """Find critical keywords present in code."""
    found: list[str] = [];
    for kw in CRITICAL_KEYWORDS {
        if kw in code {
            found.append(kw);
        }
    }
    return found;
}

can find_patterns(text: str) -> set[str] {
    """Find all critical patterns in text."""
    found: set[str] = set();
    for (pattern, name) in CRITICAL_PATTERNS {
        if re.search(pattern, text, re.IGNORECASE) {
            found.add(name);
        }
    }
    return found;
}

can should_exclude(path: object) -> bool {
    """Check if a path should be excluded from processing."""
    parts = set(path.parts);
    if parts & EXCLUDE_DIRS {
        return True;
    }
    for pattern in EXCLUDE_PATTERNS {
        if path.match(pattern) {
            return True;
        }
    }
    return False;
}

can validate_code_blocks(text: str) -> tuple[bool, str | None] {
    """Validate that code blocks are balanced."""
    fence_count = text.count("```");
    if fence_count % 2 != 0 {
        return (False, "Unbalanced code fences");
    }
    return (True, None);
}
