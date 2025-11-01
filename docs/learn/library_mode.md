# **Jac Library Mode: Pure Python with Jac's Power**

## **Introduction**

Every Jac program can be expressed as pure Python code using Jac's library mode. This means you get **100% of Jac's object-spatial programming capabilities** in regular Python syntax—no new language to learn, just powerful libraries to import.

Library mode is perfect for:
- **Python-first teams** wanting to adopt Jac gradually
- **Existing Python codebases** that need graph-based features
- **Understanding Jac's internals** by seeing the Python equivalent
- **Maximum interoperability** with Python tools and frameworks

### **Turn any Jac code example you see to Pure Python**

When you run `jac jac2lib myfile.jac`, Jac generates clean Python code that:
1. Imports from `jaclang.lib` instead of using aliased imports
2. Uses direct function calls like `spawn()` and `visit()` instead of `_jl.spawn()`
3. Produces readable, maintainable code suitable for library distribution

---

## **The Friends Network Example**

Let's walk through a complete example that demonstrates Jac's object-spatial programming in library mode.

### **The Jac Code**

Here's a social network graph with people connected by friendship and family relationships:

```jac
node Person {
    has name: str;

    can announce with FriendFinder entry {
        print(f"{visitor} is checking me out");
    }
}

edge Friend {}
edge Family {
    can announce with FriendFinder entry {
        print(f"{visitor} is traveling to family member");
    }
}

with entry {
    # Build the graph
    p1 = Person(name="John");
    p2 = Person(name="Susan");
    p3 = Person(name="Mike");
    p4 = Person(name="Alice");
    root ++> p1;
    p1 +>: Friend :+> p2;
    p2 +>: Family :+> [p1, p3];
    p2 +>: Friend :+> p3;
}

walker FriendFinder {
    has started: bool = False;

    can report_friend with Person entry {
        if self.started {
            print(f"{here.name} is a friend of friend, or family");
        } else {
            self.started = True;
            visit [-->];
        }
        visit [edge ->:Family :->];
    }

    can move_to_person with `root entry {
        visit [-->];
    }
}

with entry {
    result = FriendFinder() spawn root;
    print(result);
}
```

### **The Library Mode Python Equivalent**

Run `jac jac2lib friends.jac` to generate:

```python
from __future__ import annotations
from jaclang.lib import (
    Edge,
    Node,
    Path,
    Root,
    Walker,
    build_edge,
    connect,
    on_entry,
    refs,
    root,
    spawn,
    visit,
)


class Person(Node):
    name: str

    @on_entry
    def announce(self, visitor: FriendFinder) -> None:
        print(f"{visitor} is checking me out")


class Friend(Edge):
    pass


class Family(Edge):

    @on_entry
    def announce(self, visitor: FriendFinder) -> None:
        print(f"{visitor} is traveling to family member")


# Build the graph
p1 = Person(name="John")
p2 = Person(name="Susan")
p3 = Person(name="Mike")
p4 = Person(name="Alice")
connect(left=root(), right=p1)
connect(left=p1, right=p2, edge=Friend)
connect(left=p2, right=[p1, p3], edge=Family)
connect(left=p2, right=p3, edge=Friend)


class FriendFinder(Walker):
    started: bool = False

    @on_entry
    def report_friend(self, here: Person) -> None:
        if self.started:
            print(f"{here.name} is a friend of friend, or family")
        else:
            self.started = True
            visit(self, refs(Path(here).edge_out().visit()))
        visit(
            self,
            refs(
                Path(here).edge_out(edge=lambda i: isinstance(i, Family)).edge().visit()
            ),
        )

    @on_entry
    def move_to_person(self, here: Root) -> None:
        visit(self, refs(Path(here).edge_out().visit()))


result = spawn(FriendFinder(), root())
print(result)
```

---

## **Key Concepts Explained**

### **1. Nodes and Edges**

**In Jac:**
```jac
node Person {
    has name: str;
}

edge Friend {}
```

**In Library Mode:**
```python
from jaclang.lib import Node, Edge


class Person(Node):
    name: str


class Friend(Edge):
    pass
```

- Inherit from `Node` for graph nodes
- Inherit from `Edge` for relationships between nodes
- Use Python's class attributes for data fields

### **2. Walkers**

**In Jac:**
```jac
walker FriendFinder {
    has started: bool = False;
}
```

**In Library Mode:**
```python
from jaclang.lib import Walker


class FriendFinder(Walker):
    started: bool = False
```

- Inherit from `Walker` for graph traversal agents
- Walkers move through the graph and execute logic at each node

### **3. Abilities (Event Handlers)**

**In Jac:**
```jac
can report_friend with Person entry {
    print(f"{here.name} is a friend");
}
```

**In Library Mode:**
```python
from jaclang.lib import on_entry


@on_entry
def report_friend(self, here: Person) -> None:
    print(f"{here.name} is a friend")
```

- Use `@on_entry` decorator for entry abilities
- Use `@on_exit` decorator for exit abilities
- The `here` parameter represents the current node
- The `visitor` parameter (in node/edge abilities) represents the walker

### **4. Connecting Nodes**

**In Jac:**
```jac
root ++> p1;                      # Connect root to p1
p1 +>: Friend :+> p2;             # Connect p1 to p2 with Friend edge
p2 +>: Family :+> [p1, p3];       # Connect p2 to multiple nodes
```

**In Library Mode:**
```python
from jaclang.lib import connect, root

connect(left=root(), right=p1)
connect(left=p1, right=p2, edge=Friend)
connect(left=p2, right=[p1, p3], edge=Family)
```

- `connect()` creates directed edges between nodes
- `edge` parameter specifies the edge type
- Can connect to single nodes or lists of nodes

### **5. Spawning Walkers**

**In Jac:**
```jac
result = FriendFinder() spawn root;
```

**In Library Mode:**
```python
from jaclang.lib import spawn, root

result = spawn(FriendFinder(), root())
```

- `spawn()` starts a walker at a specific node
- `root()` returns the root node of the graph
- Returns the walker after traversal completes

### **6. Visiting Nodes**

**In Jac:**
```jac
visit [-->];                      # Visit all outgoing edges
visit [edge ->:Family :->];       # Visit only Family edges
```

**In Library Mode:**
```python
from jaclang.lib import visit, refs, Path

visit(self, refs(Path(here).edge_out().visit()))
visit(
    self, refs(Path(here).edge_out(edge=lambda i: isinstance(i, Family)).edge().visit())
)
```

- `Path()` creates a traversal path from a node
- `edge_out()` specifies outgoing edges
- `edge()` filters to edges only (not nodes)
- `visit()` marks the path for walker to follow
- `refs()` converts path to node references

---

## **Common Patterns**

### **Pattern 1: Simple Graph Traversal**

```python
from jaclang.lib import Node, Walker, spawn, visit, refs, Path, root, connect, on_entry


class Item(Node):
    value: int = 0


class Traverser(Walker):
    @on_entry
    def process(self, here: Item) -> None:
        print(f"Processing item: {here.value}")
        visit(self, refs(Path(here).edge_out().visit()))


# Build graph
items = [Item(value=i) for i in range(5)]
for i in range(len(items) - 1):
    connect(left=items[i], right=items[i + 1])
connect(left=root(), right=items[0])

# Traverse
spawn(Traverser(), root())
```

### **Pattern 2: Filtered Edge Traversal**

```python
from jaclang.lib import Node, Edge, Walker, spawn, visit, refs, Path, on_entry


class Person(Node):
    name: str


class Friend(Edge):
    pass


class Colleague(Edge):
    pass


class FriendFinder(Walker):
    @on_entry
    def find_friends(self, here: Person) -> None:
        # Only traverse Friend edges
        visit(
            self,
            refs(Path(here).edge_out(edge=lambda e: isinstance(e, Friend)).visit()),
        )
```

### **Pattern 3: Bidirectional Traversal**

```python
from jaclang.lib import Path, visit, refs

# Visit incoming edges
visit(self, refs(Path(here).edge_in().visit()))

# Visit both incoming and outgoing
visit(self, refs(Path(here).edge_any().visit()))
```

### **Pattern 4: Node Type Filtering**

```python
# Visit only Person nodes
visit(self, refs(Path(here).edge_out(node=lambda n: isinstance(n, Person)).visit()))

# Visit only edges, not nodes
visit(self, refs(Path(here).edge_out().edge().visit()))
```

### **Pattern 5: Filtering Archetype Lists**

```python
from jaclang.lib import filter_on, Node

class Task(Node):
    priority: int
    completed: bool

# Get all high priority incomplete tasks
tasks = [Task(priority=i, completed=i % 2 == 0) for i in range(10)]
high_priority = filter_on(tasks, lambda t: t.priority > 5 and not t.completed)
```

### **Pattern 6: Batch Attribute Assignment**

```python
from jaclang.lib import assign_all, Node

class Item(Node):
    status: str = ""
    version: int = 0

items = [Item() for _ in range(5)]
# Assign status and version to all items at once
assign_all(items, (("status", "version"), ("active", 2)))
```

### **Pattern 7: Working with Multiple Roots**

```python
from jaclang.lib import root, get_all_root, allow_root, elevate_root

# Get current root
current = root()

# Get all roots in the system
all_roots = get_all_root()

# Grant access from one root to another
allow_root(my_node, all_roots[0].__jac__.id, "READ")

# Elevate to system root for admin operations
elevate_root()
```

### **Pattern 8: Dynamic Archetype Creation**

```python
from jaclang.lib import create_archetype_from_source, get_archetype

# Create archetypes from Jac source code at runtime
source = """
node DataPoint {
    has x: float;
    has y: float;
}
"""

module = create_archetype_from_source(source, module_name="dynamic_nodes")
DataPoint = get_archetype("dynamic_nodes", "DataPoint")
point = DataPoint(x=1.0, y=2.0)
```

### **Pattern 9: Persistence and Graph Management**

```python
from jaclang.lib import save, object_ref, get_object, commit, reset_graph

# Save a node to make it persistent
person = Person(name="Alice")
save(person)

# Get its ID for later retrieval
person_id = object_ref(person)

# Retrieve it later
retrieved = get_object(person_id)

# Commit all changes to datasource
commit()

# Clear entire graph (careful!)
deleted_count = reset_graph()
```

### **Pattern 10: Threading for Parallel Operations**

```python
from jaclang.lib import thread_run, thread_wait

def expensive_computation(data):
    # Some heavy processing
    return sum(data)

# Run in background thread
future = thread_run(expensive_computation, range(1000000))

# Do other work...

# Wait for result when needed
result = thread_wait(future)
```

---

## **Advanced Features**

### **Semantic Strings (AI Integration)**

```python
from jaclang.lib import sem, by


# Add semantic metadata to classes
@sem(
    "Returns the weather for a given city.",
    {"city": "Name of the city to get weather for"},
)
class Weather(Node):
    city: str
    temp: float


# Use LLM-powered functions (requires byllm package)
@by(model)
def analyze_sentiment(text: str) -> str:
    """Analyze the sentiment of the given text."""
    pass  # Implementation generated by LLM
```

### **Data Persistence & Object Management**

```python
from jaclang.lib import save, object_ref, get_object, commit, destroy

# Save a node to database
person = Person(name="Alice")
save(person)

# Get unique ID (hex string)
node_id = object_ref(person)

# Retrieve by ID later
retrieved_person = get_object(node_id)

# Commit changes to datasource
commit(person)

# Delete archetype from memory
destroy(person)
```

### **Fine-Grained Access Control**

```python
from jaclang.lib import (
    perm_grant, perm_revoke, allow_root, disallow_root,
    check_read_access, check_write_access, check_connect_access, elevate_root
)

# Grant public read access to archetype
perm_grant(node, "READ")

# Revoke public access
perm_revoke(node)

# Allow specific root to access this node
allow_root(node, root_id, "WRITE")

# Disallow specific root access
disallow_root(node, root_id, "READ")

# Check permissions before operations
if check_write_access(node.__jac__):
    node.value = 42

# Elevate to system root for admin operations
elevate_root()
```

### **Dynamic Module Loading**

```python
from jaclang.lib import (
    jac_import, create_archetype_from_source, get_archetype,
    spawn_node, spawn_walker, update_walker
)

# Import Jac module dynamically
jac_import("my_module", "./path/to/modules")

# Create archetypes from source code at runtime
source_code = """
node Task {
    has description: str;
    has priority: int = 0;
}
"""
module = create_archetype_from_source(source_code, "dynamic_tasks")

# Get and use the dynamically created archetype
Task = get_archetype("dynamic_tasks", "Task")
task = Task(description="Complete documentation", priority=1)

# Spawn node by name string
node = spawn_node("Task", {"description": "Test", "priority": 5}, "dynamic_tasks")

# Spawn walker by name string
walker = spawn_walker("TaskProcessor", {}, "__main__")

# Hot-reload walker from module
update_walker("my_module", {"TaskProcessor": None})
```

### **Graph Introspection**

```python
from jaclang.lib import (
    list_modules, list_nodes, list_walkers, list_edges,
    get_edges, edges_to_nodes, get_edges_with_node
)

# List all loaded modules
modules = list_modules()

# List archetypes in a module
nodes = list_nodes("my_module")
walkers = list_walkers("my_module")
edges = list_edges("my_module")

# Get edges connected to nodes
from jaclang.lib import ObjectSpatialPath, EdgeDir
path = ObjectSpatialPath([node], [])
connected_edges = get_edges([node], path.destinations[0])

# Get both edges and connected nodes
edges_and_nodes = get_edges_with_node([node], path.destinations[0])
```

---

## **Complete Library Interface Reference**

### **Type Aliases & Constants**

| Name | Type | Description |
|------|------|-------------|
| `TYPE_CHECKING` | bool | Python typing constant for type checking blocks |
| `EdgeDir` | Enum | Edge direction enum (IN, OUT, ANY) |
| `DSFunc` | Type | Data spatial function type alias |

### **Base Classes**

| Class | Description | Usage |
|-------|-------------|-------|
| `Obj` | Base class for all archetypes | Generic archetype base |
| `Node` | Graph node archetype | `class MyNode(Node):` |
| `Edge` | Graph edge archetype | `class MyEdge(Edge):` |
| `Walker` | Graph traversal agent | `class MyWalker(Walker):` |
| `Root` | Root node type | Entry point for graphs |
| `GenericEdge` | Generic edge when no type specified | Default edge type |
| `Path` | Object-spatial path builder | `Path(node).edge_out()` |

### **Decorators**

| Decorator | Description | Usage |
|-----------|-------------|-------|
| `@on_entry` | Entry ability decorator | Executes when walker enters node/edge |
| `@on_exit` | Exit ability decorator | Executes when walker exits node/edge |
| `@sem(doc, fields)` | Semantic string decorator | AI/LLM integration metadata |

### **Graph Construction**

| Function | Description | Parameters |
|----------|-------------|------------|
| `connect(left, right, edge, undir, conn_assign, edges_only)` | Connect nodes with edge | `left`: source node(s)<br>`right`: target node(s)<br>`edge`: edge class (optional)<br>`undir`: undirected flag<br>`conn_assign`: attribute assignments<br>`edges_only`: return edges instead of nodes |
| `disconnect(left, right, dir, filter)` | Remove edges between nodes | `left`: source node(s)<br>`right`: target node(s)<br>`dir`: edge direction<br>`filter`: edge filter function |
| `build_edge(is_undirected, conn_type, conn_assign)` | Create edge builder function | `is_undirected`: bidirectional flag<br>`conn_type`: edge class<br>`conn_assign`: initial attributes |
| `assign_all(target, attr_val)` | Assign attributes to list of objects | `target`: list of objects<br>`attr_val`: tuple of (attrs, values) |

### **Graph Traversal & Walker Operations**

| Function | Description | Parameters |
|----------|-------------|------------|
| `spawn(walker, node)` | Start walker at node | `walker`: Walker instance<br>`node`: Starting node |
| `spawn_call(walker, node)` | Internal spawn execution (sync) | `walker`: Walker anchor<br>`node`: Node/edge anchor |
| `async_spawn_call(walker, node)` | Internal spawn execution (async) | Same as spawn_call (async version) |
| `visit(walker, nodes)` | Visit specified nodes | `walker`: Walker instance<br>`nodes`: Node/edge references |
| `disengage(walker)` | Stop walker traversal | `walker`: Walker to stop |
| `refs(path)` | Convert path to node/edge references | `path`: ObjectSpatialPath |
| `arefs(path)` | Async path references (placeholder) | `path`: ObjectSpatialPath |
| `filter_on(items, func)` | Filter archetype list by predicate | `items`: list of archetypes<br>`func`: filter function |

### **Path Building (Methods on Path class)**

| Method | Description | Returns |
|--------|-------------|---------|
| `Path(node)` | Create path from node | ObjectSpatialPath |
| `.edge_out(edge, node)` | Filter outgoing edges | Self (chainable) |
| `.edge_in(edge, node)` | Filter incoming edges | Self (chainable) |
| `.edge_any(edge, node)` | Filter any direction | Self (chainable) |
| `.edge()` | Edges only (no nodes) | Self (chainable) |
| `.visit()` | Mark for visit traversal | Self (chainable) |

### **Node & Edge Operations**

| Function | Description | Parameters |
|----------|-------------|------------|
| `get_edges(origin, destination)` | Get edges connected to nodes | `origin`: list of nodes<br>`destination`: ObjectSpatialDestination |
| `get_edges_with_node(origin, destination, from_visit)` | Get edges and connected nodes | `origin`: list of nodes<br>`destination`: destination spec<br>`from_visit`: include nodes flag |
| `edges_to_nodes(origin, destination)` | Get nodes connected via edges | `origin`: list of nodes<br>`destination`: destination spec |
| `remove_edge(node, edge)` | Remove edge reference from node | `node`: NodeAnchor<br>`edge`: EdgeAnchor |
| `detach(edge)` | Detach edge from both nodes | `edge`: EdgeAnchor |

### **Data Access & Persistence**

| Function | Description | Returns |
|----------|-------------|---------|
| `root()` | Get current root node | Root node instance |
| `get_all_root()` | Get all root nodes | List of roots |
| `get_object(id)` | Get archetype by ID string | Archetype or None |
| `object_ref(obj)` | Get hex ID string of archetype | String |
| `save(obj)` | Persist archetype to database | None |
| `destroy(objs)` | Delete archetype(s) from memory | None |
| `commit(anchor)` | Commit data to datasource | None |
| `reset_graph(root)` | Purge graph from memory | Count of deleted items |

### **Access Control & Permissions**

| Function | Description | Parameters |
|----------|-------------|------------|
| `perm_grant(archetype, level)` | Grant public access to archetype | `archetype`: Target archetype<br>`level`: AccessLevel (READ/CONNECT/WRITE) |
| `perm_revoke(archetype)` | Revoke public access | `archetype`: Target archetype |
| `allow_root(archetype, root_id, level)` | Allow specific root access | `archetype`: Target<br>`root_id`: Root UUID<br>`level`: Access level |
| `disallow_root(archetype, root_id, level)` | Disallow specific root access | Same as allow_root |
| `elevate_root()` | Elevate context to system root | No parameters (uses context) |
| `check_read_access(anchor)` | Check read permission | `anchor`: Target anchor |
| `check_write_access(anchor)` | Check write permission | `anchor`: Target anchor |
| `check_connect_access(anchor)` | Check connect permission | `anchor`: Target anchor |
| `check_access_level(anchor, no_custom)` | Get access level for anchor | `anchor`: Target<br>`no_custom`: skip custom check |

### **Module Management & Archetypes**

| Function | Description | Parameters |
|----------|-------------|------------|
| `jac_import(target, base_path, ...)` | Import Jac/Python module | `target`: Module name<br>`base_path`: Search path<br>`absorb`, `mdl_alias`, `override_name`, `items`, `reload_module`, `lng`: import options |
| `load_module(module_name, module, force)` | Load module into machine | `module_name`: Name<br>`module`: Module object<br>`force`: reload flag |
| `attach_program(program)` | Attach JacProgram to runtime | `program`: JacProgram instance |
| `list_modules()` | List all loaded modules | Returns list of names |
| `list_nodes(module_name)` | List nodes in module | `module_name`: Module to inspect |
| `list_walkers(module_name)` | List walkers in module | `module_name`: Module to inspect |
| `list_edges(module_name)` | List edges in module | `module_name`: Module to inspect |
| `get_archetype(module_name, archetype_name)` | Get archetype class from module | `module_name`: Module<br>`archetype_name`: Class name |
| `make_archetype(cls)` | Convert class to archetype | `cls`: Class to convert |
| `spawn_node(node_name, attributes, module_name)` | Create node instance by name | `node_name`: Node class name<br>`attributes`: Init dict<br>`module_name`: Source module |
| `spawn_walker(walker_name, attributes, module_name)` | Create walker instance by name | `walker_name`: Walker class<br>`attributes`: Init dict<br>`module_name`: Source module |
| `update_walker(module_name, items)` | Reload walker from module | `module_name`: Module<br>`items`: Items to update |
| `create_archetype_from_source(source_code, ...)` | Create archetype from Jac source | `source_code`: Jac code string<br>`module_name`, `base_path`, `cachable`, `keep_temporary_files`: options |

### **Testing & Debugging**

| Function | Description | Parameters |
|----------|-------------|------------|
| `jac_test(func)` | Mark function as test | `func`: Test function |
| `run_test(filepath, ...)` | Run test suite | `filepath`: Test file<br>`func_name`, `filter`, `xit`, `maxfail`, `directory`, `verbose`: test options |
| `report(expr, custom)` | Report value from walker | `expr`: Value to report<br>`custom`: custom report flag |
| `printgraph(node, depth, traverse, edge_type, bfs, edge_limit, node_limit, file, format)` | Generate graph visualization | `node`: Start node<br>`depth`: Max depth<br>`traverse`: traversal flag<br>`edge_type`: filter edges<br>`bfs`: breadth-first flag<br>`edge_limit`, `node_limit`: limits<br>`file`: output path<br>`format`: 'dot' or 'mermaid' |

### **LLM & AI Integration**

| Function | Description | Use Case |
|----------|-------------|----------|
| `by(model)` | Decorator for LLM-powered functions | `@by(model) def func(): ...` |
| `call_llm(model, mtir)` | Direct LLM invocation | Advanced LLM usage |
| `get_mtir(caller, args, call_params)` | Get method IR for LLM | LLM internal representation |
| `sem(semstr, inner_semstr)` | Semantic metadata decorator | `@sem("doc", {"field": "desc"})` |

### **Runtime & Threading**

| Function | Description | Parameters |
|----------|-------------|------------|
| `setup()` | Initialize class references | No parameters |
| `get_context()` | Get current execution context | Returns ExecutionContext |
| `field(factory, init)` | Define dataclass field | `factory`: Default factory<br>`init`: Include in init |
| `impl_patch_filename(file_loc)` | Patch function file location | `file_loc`: File path for stack traces |
| `thread_run(func, *args)` | Run function in thread | `func`: Function<br>`args`: Arguments |
| `thread_wait(future)` | Wait for thread completion | `future`: Future object |
| `create_cmd()` | Create CLI commands | No parameters (placeholder) |

---

## **Best Practices**

### **1. Type Hints**

Always use type hints for better IDE support:

```python
from typing import Optional


class Person(Node):
    name: str
    age: Optional[int] = None
```

### **2. Walker State**

Keep walker state minimal and immutable when possible:

```python
class Counter(Walker):
    count: int = 0  # Simple state

    @on_entry
    def increment(self, here: Node) -> None:
        self.count += 1
```

### **3. Path Filtering**

Use lambda functions for flexible filtering:

```python
# Filter by edge type
visit(
    self,
    refs(Path(here).edge_out(edge=lambda e: isinstance(e, (Friend, Family))).visit()),
)

# Filter by node attribute
visit(
    self,
    refs(Path(here).edge_out(node=lambda n: hasattr(n, "active") and n.active).visit()),
)
```

### **4. Clean Imports**

Import only what you need:

```python
# Good
from jaclang.lib import Node, Walker, spawn, visit, on_entry

# Avoid
from jaclang.lib import *
```

---

## **Migration Guide**

### **From Jac to Library Mode**

| Jac Syntax | Library Mode Python |
|------------|---------------------|
| `node Person { has name: str; }` | `class Person(Node):`<br>&nbsp;&nbsp;&nbsp;&nbsp;`name: str` |
| `edge Friend {}` | `class Friend(Edge):`<br>&nbsp;&nbsp;&nbsp;&nbsp;`pass` |
| `walker W { has x: int; }` | `class W(Walker):`<br>&nbsp;&nbsp;&nbsp;&nbsp;`x: int` |
| `root ++> node` | `connect(root(), node)` |
| `a +>: Edge :+> b` | `connect(a, b, Edge)` |
| `W() spawn root` | `spawn(W(), root())` |
| `visit [-->]` | `visit(self, refs(Path(here).edge_out().visit()))` |
| `visit [<--]` | `visit(self, refs(Path(here).edge_in().visit()))` |
| `visit [--]` | `visit(self, refs(Path(here).edge_any().visit()))` |
| `can f with T entry {}` | `@on_entry`<br>`def f(self, here: T): ...` |
| `disengage;` | `disengage(self)` |

---

## **Summary**

Library mode demonstrates that **Jac is Python**—just with powerful abstractions for object-spatial programming. You get:

✅ **100% Feature Parity**: Everything Jac can do, library mode can do
✅ **Clean Python**: No magic, just classes, decorators, and functions
✅ **Full IDE Support**: Type hints, autocomplete, and debugging work perfectly
✅ **Easy Integration**: Drop into any Python project without friction
✅ **Readable Output**: Generated code is maintainable and understandable

Whether you write `.jac` files or use library mode directly, you're writing Python with superpowers for graph-based, AI-native applications.
