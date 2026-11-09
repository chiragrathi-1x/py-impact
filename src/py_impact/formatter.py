import json
from typing import List, Set, Dict
from .models import ProjectGraph, Symbol

def format_tree(graph: ProjectGraph, start_fqn: str) -> str:
    """Generates a visual tree string of callers (upstream) iteratively to avoid recursion limits."""
    lines = []
    # Stack stores (fqn, depth)
    stack = [(start_fqn, 0)]
    visited = set()
    
    while stack:
        curr_fqn, depth = stack.pop()
        indent = "  " * depth
        
        if curr_fqn in visited:
            lines.append(f"{indent}- {curr_fqn} (already visited)")
            continue
            
        lines.append(f"{indent}- {curr_fqn}")
        visited.add(curr_fqn)
        
        parents = graph.incoming.get(curr_fqn, set())
        # Sort reversed for alphabetical popping order
        for p in sorted(parents, reverse=True):
            stack.append((p, depth + 1))
            
    return "\n".join(lines) + "\n"

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
