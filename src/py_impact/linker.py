import ast
from pathlib import Path
from typing import Dict, List, Set
from .models import ProjectGraph, Symbol
from .parser import ImportResolver

class CallLinker(ast.NodeVisitor):
    """Pass 2: Identifies calls and links them to defined symbols."""
    def __init__(self, 
                 file_path: Path, 
                 module_fqn: str, 
                 graph: ProjectGraph, 
                 import_map: Dict[str, str]):
        self.file_path = file_path
        self.module_fqn = module_fqn
        self.graph = graph
        self.import_map = import_map
        self.scope_stack: List[str] = [module_fqn]

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope_stack.append(f"{self.scope_stack[-1]}.{node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope_stack.append(f"{self.scope_stack[-1]}.{node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.scope_stack.append(f"{self.scope_stack[-1]}.{node.name}")
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call):
        callee_fqn = self._resolve_name(node.func)
        if callee_fqn and callee_fqn in self.graph.symbols:
            # Link current scope to the target
            caller = self.scope_stack[-1]
            self.graph.add_edge(caller, callee_fqn, node.lineno)
        self.generic_visit(node)

    def _resolve_name(self, node: ast.AST) -> str | None:
        """Attempts to find the FQN of a call target."""
        if isinstance(node, ast.Name):
            # Local lookup or imported lookup
            name = node.id
            # 1. Is it imported?
            if name in self.import_map:
                return self.import_map[name]
            # 2. Is it in the same module?
            local_fqn = f"{self.module_fqn}.{name}"
            if local_fqn in self.graph.symbols:
                return local_fqn
            # 3. Is it inside a class (if we are in a class)?
            # Simplification: we don't handle 'self.' resolution deeply here,
            # but we can resolve simple calls within the same module.
        
        elif isinstance(node, ast.Attribute):
            # Handle Class.method or module.function
            value_fqn = self._resolve_name(node.value)
            if value_fqn:
                return f"{value_fqn}.{node.attr}"
        
        return None
