import unittest
from pathlib import Path
from py_impact.parser import get_module_fqn, ImportResolver
import ast

class TestUnits(unittest.TestCase):
    def test_module_fqn_resolution(self):
        root = Path("/project/src")
        f1 = Path("/project/src/module/sub.py")
        f2 = Path("/project/src/module/__init__.py")
        
        # Simulate absolute resolution for consistency in tests
        # In real tests we'd use actual temp paths, but string/stem logic is internal
        self.assertEqual(get_module_fqn(root, f1), "module.sub")
        self.assertEqual(get_module_fqn(root, f2), "module")

    def test_import_resolver_absolute(self):
        code = "import os\nimport numpy as np\nfrom mypkg import tools"
        tree = ast.parse(code)
        resolver = ImportResolver("test_mod")
        resolver.visit(tree)
        
        self.assertEqual(resolver.imports["os"], "os")
        self.assertEqual(resolver.imports["np"], "numpy")
        self.assertEqual(resolver.imports["tools"], "mypkg.tools")

    def test_import_resolver_relative(self):
        # Current module: a.b.c
        # from . import d -> a.b.d
        # from .. import e -> a.e
        code = "from . import sibling\nfrom ..parent_mod import uncle"
        tree = ast.parse(code)
        resolver = ImportResolver("a.b.c")
        resolver.visit(tree)
        
        self.assertEqual(resolver.imports["sibling"], "a.b.sibling")
        self.assertEqual(resolver.imports["uncle"], "a.parent_mod.uncle")

if __name__ == "__main__":
    unittest.main()