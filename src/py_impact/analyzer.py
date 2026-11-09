import ast
import logging
from pathlib import Path
from typing import List, Set, Dict, Optional
from .models import ProjectGraph, Symbol
from .parser import DefinitionCrawler, ImportResolver, get_module_fqn, find_source_root
from .linker import CallLinker

logger = logging.getLogger(__name__)

class Analyzer:
    def __init__(self, search_path: Path, exclude_patterns: List[str] = None):
        self.search_path = search_path.resolve()
        self.source_root = find_source_root(self.search_path)
        self.exclude_patterns = exclude_patterns or []
        self.graph = ProjectGraph()
        self.module_imports: Dict[str, Dict[str, str]] = {}

    def _should_exclude(self, path: Path) -> bool:
        str_path = str(path)
        return any(p in str_path for p in self.exclude_patterns)

    def run(self):
        """Executes the multi-pass analysis."""
        py_files = [p for p in self.search_path.rglob("*.py") if not self._should_exclude(p)]

        # Pass 1: Crawl definitions
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                mod_fqn = get_module_fqn(self.source_root, py_file)
                
                crawler = DefinitionCrawler(py_file, mod_fqn)
                crawler.visit(tree)
                for sym in crawler.symbols:
                    self.graph.add_symbol(sym)
                
                importer = ImportResolver(mod_fqn)
                importer.visit(tree)
                self.module_imports[mod_fqn] = importer.imports
                
            except (SyntaxError, UnicodeDecodeError) as e:
                logger.error(f"Failed to parse {py_file}: {e}")

        # Pass 2: Link calls
        for py_file in py_files:
            mod_fqn = get_module_fqn(self.source_root, py_file)
            if mod_fqn not in self.module_imports:
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                linker = CallLinker(
                    py_file, 
                    mod_fqn, 
                    self.graph, 
                    self.module_imports[mod_fqn]
                )
                linker.visit(tree)
            except Exception as e:
                logger.error(f"Error linking {py_file}: {e}")

    def get_blast_radius(self, target_fqn: str) -> Set[str]:
        """Returns all symbols that eventually call the target (upstream)."""
        visited = set()
        to_visit = [target_fqn]
        
        while to_visit:
            current = to_visit.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            parents = self.graph.incoming.get(current, set())
            for p in parents:
                if p not in visited:
                    to_visit.append(p)
        
        visited.discard(target_fqn)
        return visited

    def get_orphans(self) -> List[Symbol]:
        """Symbols with no incoming edges, excluding common entry points."""
        orphans = []
        entry_points = {"main", "__init__"}
        
        for fqn, sym in self.graph.symbols.items():
            if sym.type not in ('function', 'class'):
                continue
            
            if sym.name in entry_points:
                continue

            if fqn not in self.graph.incoming or not self.graph.incoming[fqn]:
                orphans.append(sym)
        return orphans

    def get_hotspots(self, limit: int = 10) -> List[tuple[str, int]]:
        """Symbols with the most incoming edges."""
        counts = {fqn: len(callers) for fqn, callers in self.graph.incoming.items()}
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:limit]
