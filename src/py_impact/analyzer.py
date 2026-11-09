import ast
import logging
from pathlib import Path
from typing import List, Set, Dict, Optional
from .models import ProjectGraph, Symbol
from .parser import DefinitionCrawler, ImportResolver, get_module_fqn
from .linker import CallLinker

logger = logging.getLogger(__name__)

class Analyzer:
    def __init__(self, root_dir: Path, exclude_patterns: List[str] = None):
        self.root_dir = root_dir.resolve()
        self.exclude_patterns = exclude_patterns or []
        self.graph = ProjectGraph()
        # Maps module_fqn -> dict of imports
        self.module_imports: Dict[str, Dict[str, str]] = {}

    def _should_exclude(self, path: Path) -> bool:
        str_path = str(path)
        return any(p in str_path for p in self.exclude_patterns)

    def run(self):
        """Executes the multi-pass analysis."""
        py_files = [p for p in self.root_dir.rglob("*.py") if not self._should_exclude(p)]

        # Pass 1: Crawl definitions
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                mod_fqn = get_module_fqn(self.root_dir, py_file)
                
                # Index symbols
                crawler = DefinitionCrawler(py_file, mod_fqn)
                crawler.visit(tree)
                for sym in crawler.symbols:
                    self.graph.add_symbol(sym)
                
                # Index imports for Pass 2
                importer = ImportResolver(mod_fqn)
                importer.visit(tree)
                self.module_imports[mod_fqn] = importer.imports
                
            except (SyntaxError, UnicodeDecodeError) as e:
                logger.error(f"Failed to parse {py_file}: {e}")

        # Pass 2: Link calls
        for py_file in py_files:
            mod_fqn = get_module_fqn(self.root_dir, py_file)
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
        
        # Remove the target itself from the result
        visited.discard(target_fqn)
        return visited

    def get_orphans(self) -> List[Symbol]:
        """Symbols with no incoming edges from within the project."""
        orphans = []
        for fqn, sym in self.graph.symbols.items():
            # We exclude modules themselves and only look at functions/classes
            # Also exclude __init__ or common entry points if desired, 
            # but here we follow strict 0-incoming rule.
            if fqn not in self.graph.incoming:
                # Only count symbols that aren't modules
                if sym.type in ('function', 'class'):
                    orphans.append(sym)
        return orphans

    def get_hotspots(self, limit: int = 10) -> List[tuple[str, int]]:
        """Symbols with the most incoming edges."""
        counts = {fqn: len(callers) for fqn, callers in self.graph.incoming.items()}
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:limit]
