import json
from typing import List, Set, Dict
from .models import ProjectGraph, Symbol

def format_tree(graph: ProjectGraph, start_fqn: str, visited: Set[str] = None, indent: int = 0) -> str:
    """Generates a visual tree string of callers (upstream)."""
    if visited is None:
        visited = set()
    
    res = "  " * indent + f"- {start_fqn}\n"
    visited.add(start_fqn)
    
    parents = graph.incoming.get(start_fqn, set())
    for p in sorted(parents):
        if p not in visited:
            res += format_tree(graph, p, visited, indent + 1)
        else:
            res += "  " * (indent + 1) + f"- {p} (circular)\n"
            
    return res

def export_dot(graph: ProjectGraph) -> str:
    """Generates DOT format for Graphviz."""
    lines = ["digraph CallGraph {", "  rankdir=LR;", "  node [shape=box, fontname=\"Courier\"];"]
    for fqn in graph.symbols:
        lines.append(f'  "{fqn}";')
    
    for edge in graph.edges:
        lines.append(f'  "{edge.caller_fqn}" -> "{edge.callee_fqn}";')
    
    lines.append("}")
    return "\n".join(lines)

def export_json(graph: ProjectGraph) -> str:
    """Generates JSON representation."""
    data = {
        "symbols": {fqn: {"file": str(s.file_path), "line": s.line_start, "type": s.type} 
                    for fqn, s in graph.symbols.items()},
        "calls": [{"from": e.caller_fqn, "to": e.callee_fqn, "line": e.lineno} 
                  for e in graph.edges]
    }
    return json.dumps(data, indent=2)
