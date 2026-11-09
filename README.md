# PyImpact

**PyImpact** is a static analysis tool designed to map internal Python call graphs and identify the "blast radius" of code changes. It helps developers understand which upstream modules and functions will be affected when a specific line of code or function is modified, eliminating the guesswork in refactoring.

## Features

- **Recursive AST Parsing**: Automatically indexes function and class definitions across your entire project directory.
- **Blast Radius Calculation**: Identifies every upstream caller that eventually leads to a specific target line or function.
- **Orphan Detection**: Find "dead code"—functions and classes that are defined but never referenced within the project scope.
- **Import Resolution**: Robust handling of absolute and relative imports, including aliased imports (`import x as y`).
- **Complexity Hotspots**: Rank functions by their dependency count to identify high-risk areas of the codebase.
- **Visual CLI Output**: Interactive-style tree view showing call hierarchies directly in the terminal.
- **Export Formats**: Generate JSON or DOT files for integration with Graphviz and other visualization tools.

## Installation

PyImpact requires Python 3.10+.

```bash
# From source
git clone https://github.com/user/py-impact.git
cd py-impact
pip install .
```

## Quick Start

To analyze a project and see what calls a specific function:

```bash
py-impact analyze ./src --target utils.py:42
```

To find all unused functions (orphans):

```bash
py-impact orphans ./src --exclude tests/
```

To identify the most heavily depended-upon functions:

```bash
py-impact hotspots ./src --limit 10
```

## CLI Usage

- `analyze <path>`: Build the call graph and query specific impact points.
- `orphans <path>`: List all defined symbols that have no internal callers.
- `hotspots <path>`: List symbols with the highest incoming edge count.
- `graph <path>`: Export the project structure to a graph format.

## Limitations

- **Static Analysis**: PyImpact uses the Abstract Syntax Tree (AST). It cannot resolve dynamic calls made via `getattr()`, `setattr()`, or string-based imports (e.g., `importlib.import_module`).
- **Type Hinting**: While it leverages type hints where available for better resolution, it does not perform full runtime type inference.
- **External Libraries**: PyImpact focuses on the internal project scope. Calls to third-party libraries are acknowledged but not recursively mapped unless the source is provided in the analysis path.

## Contributing

Contributions are welcome! Please ensure that any new features include corresponding test cases in the `tests/` directory. PyImpact aims to maintain high coverage of edge cases, including nested functions, decorators, and circular imports.

1. Fork the repository.
2. Create a feature branch.
3. Submit a Pull Request with a clear description of the change.

## License

This project is intended for open-source use. See the project repository for licensing details.