import dataclasses
from pathlib import Path
from typing import Dict, List, Optional, Set

@dataclasses.dataclass(frozen=True)
class Symbol:
    """Represents a function or class definition."""
    fqn: str  # Fully Qualified Name, e.g., 'pkg.module.ClassName.method_name'
    name: str
    file_path: Path
    line_start: int
    line_end: int
    type: str  # 'function' or 'class'
    parent_fqn: Optional[str] = None

    def contains_line(self, line: int) -> bool:
        return self.line_start <= line <= self.line_end

@dataclasses.dataclass
class CallEdge:
    """Represents a call from one symbol to another."""
    caller_fqn: str
    callee_fqn: str
    lineno: int

class ProjectGraph:
    """Storage for nodes (Symbols) and edges (Calls)."""
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        # Key: callee_fqn, Value: Set of caller_fqns (for blast radius/in-degree)
        self.incoming: Dict[str, Set[str]] = {}
        # Key: caller_fqn, Value: Set of callee_fqns (for out-degree)
        self.outgoing: Dict[str, Set[str]] = {}
        self.edges: List[CallEdge] = []

    def add_symbol(self, symbol: Symbol):
        self.symbols[symbol.fqn] = symbol

    def add_edge(self, caller: str, callee: str, lineno: int):
        if caller not in self.outgoing:
            self.outgoing[caller] = set()
        if callee not in self.incoming:
            self.incoming[callee] = set()
        
        self.outgoing[caller].add(callee)
        self.incoming[callee].add(caller)
        self.edges.append(CallEdge(caller, callee, lineno))

    def find_symbol_at_line(self, file_path: Path, lineno: int) -> Optional[Symbol]:
        # Find the most specific (nested) symbol containing the line
        candidates = [
            s for s in self.symbols.values() 
            if s.file_path.resolve() == file_path.resolve() and s.contains_line(lineno)
        ]
        if not candidates:
            return None
        # Sort by length of FQN descending to get the innermost definition
        return sorted(candidates, key=lambda x: len(x.fqn), reverse=True)[0]
