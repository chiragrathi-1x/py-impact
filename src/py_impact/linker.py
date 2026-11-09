import ast
from pathlib import Path
from typing import Dict, List, Set, Optional
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
        fqn = f"{self.scope_stack[-1]}.{node.name}"
        self.scope_stack.append(fqn)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        fqn = f"{self.scope_stack[-1]}.{node.name}"
        self.scope_stack.append(fqn)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        fqn = f"{self.scope_stack[-1]}.{node.name}"
        self.scope_stack.append(fqn)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call):
        callee_fqn = self._resolve_name(node.func)
        if callee_fqn and callee_fqn in self.graph.symbols:
            caller = self.scope_stack[-1]
            self.graph.add_edge(caller, callee_fqn, node.lineno)
        self.generic_visit(node)

    def _resolve_name(self, node: ast.AST) -> Optional[str]:
        """Attempts to find the FQN of a call target using scope-aware resolution."""
        if isinstance(node, ast.Name):
            name = node.id
            # 1. Check imports
            if name in self.import_map:
                return self.import_map[name]
            
            # 2. Traverse scope stack from innermost outwards
            for scope_fqn in reversed(self.scope_stack):
                target = f"{scope_fqn}.{name}"
                if target in self.graph.symbols:
                    return target
            
            # 3. Fallback to module scope if not in stack explicitly
            mod_target = f"{self.module_fqn}.{name}"
            if mod_target in self.graph.symbols:
                return mod_target
        
        elif isinstance(node, ast.Attribute):
            # Handle instance method calls: self.method()
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                for scope_fqn in reversed(self.scope_stack):
                    sym = self.graph.symbols.get(scope_fqn)
                    if sym and sym.type == 'class':
                        target = f"{scope_fqn}.{node.attr}"
                        if target in self.graph.symbols:
                            return target
                return None

            # Handle Class.method or module.function recursively
            value_fqn = self._resolve_name(node.value)
            if value_fqn:
                target = f"{value_fqn}.{node.attr}"
                if target in self.graph.symbols:
                    return target
        
        return None
