import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .models import Symbol

class DefinitionCrawler(ast.NodeVisitor):
    """Pass 1: Maps all function and class definitions to their FQNs."""
    def __init__(self, file_path: Path, module_fqn: str):
        self.file_path = file_path
        self.module_fqn = module_fqn
        self.symbols: List[Symbol] = []
        self.scope_stack: List[str] = [module_fqn]

    def visit_ClassDef(self, node: ast.ClassDef):
        fqn = f"{self.scope_stack[-1]}.{node.name}"
        self.symbols.append(Symbol(
            fqn=fqn,
            name=node.name,
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            type='class',
            parent_fqn=self.scope_stack[-1] if len(self.scope_stack) > 1 else None
        ))
        self.scope_stack.append(fqn)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_func(node)

    def _handle_func(self, node: ast.AST):
        fqn = f"{self.scope_stack[-1]}.{node.name}"
        self.symbols.append(Symbol(
            fqn=fqn,
            name=getattr(node, 'name', 'unknown'),
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            type='function',
            parent_fqn=self.scope_stack[-1] if len(self.scope_stack) > 1 else None
        ))
        self.scope_stack.append(fqn)
        self.generic_visit(node)
        self.scope_stack.pop()

class ImportResolver(ast.NodeVisitor):
    """Helper to track imports within a module."""
    def __init__(self, current_module: str):
        self.current_module = current_module
        # Maps alias -> full path (e.g., 'np' -> 'numpy')
        self.imports: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = alias.name

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        # Handle relative imports
        if node.level > 0:
            parts = self.current_module.split('.')
            # . is level 1 (current), .. is level 2 (parent)
            base = ".".join(parts[:-(node.level)]) if node.level < len(parts) else ""
            module = f"{base}.{module}" if module else base

        for alias in node.names:
            name = alias.asname or alias.name
            if alias.name == "*":
                continue # Star imports are hard for static analysis
            self.imports[name] = f"{module}.{alias.name}"

def find_source_root(path: Path) -> Path:
    """
    Detects the package root by looking for the highest directory containing an __init__.py.
    Returns the parent of that directory, or the provided path if no __init__.py is found.
    """
    current = path.resolve()
    if current.is_file():
        current = current.parent
    
    highest_pkg = None
    probe = current
    while (probe / "__init__.py").exists():
        highest_pkg = probe
        if probe.parent == probe:
            break
        probe = probe.parent
        
    return highest_pkg.parent if highest_pkg else current

def get_module_fqn(root: Path, file_path: Path) -> str:
    """Converts a file path to a dot-notation module name relative to the source root."""
    try:
        # Ensure we use absolute paths for relative_to
        root_abs = root.resolve()
        file_abs = file_path.resolve()
        relative = file_abs.relative_to(root_abs)
        parts = list(relative.parts)
        if not parts:
            return file_abs.stem
        if parts[-1] == "__init__.py":
            parts.pop()
        else:
            parts[-1] = parts[-1].removesuffix(".py")
        return ".".join(parts)
    except ValueError:
        return file_path.stem
