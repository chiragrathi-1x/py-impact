import unittest
import tempfile
import shutil
from pathlib import Path
from py_impact.analyzer import Analyzer

class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.src_dir = self.test_dir / "src"
        self.src_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_file(self, name: str, content: str):
        path = self.src_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_blast_radius_basic(self):
        self.create_file("a.py", "def base_func():\n    return 1")
        self.create_file("b.py", "from .a import base_func\ndef caller():\n    return base_func()")
        self.create_file("c.py", "from .b import caller\ndef top_level():\n    return caller()")

        analyzer = Analyzer(self.src_dir)
        analyzer.run()

        radius = analyzer.get_blast_radius("a.base_func")
        self.assertIn("b.caller", radius)
        self.assertIn("c.top_level", radius)
        self.assertEqual(len(radius), 2)

    def test_orphans_detection(self):
        self.create_file("util.py", "def unused():\n    pass\ndef used():\n    pass")
        self.create_file("main.py", "from .util import used\ndef app():\n    used()")
        
        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        orphans = [o.fqn for o in analyzer.get_orphans()]
        self.assertIn("util.unused", orphans)
        self.assertIn("main.app", orphans)
        self.assertNotIn("util.used", orphans)

    def test_hotspots(self):
        self.create_file("core.py", "def popular():\n    pass")
        self.create_file("u1.py", "from .core import popular\ndef f1(): popular()")
        self.create_file("u2.py", "from .core import popular\ndef f2(): popular()")

        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        hotspots = analyzer.get_hotspots()
        self.assertEqual(hotspots[0][0], "core.popular")
        self.assertEqual(hotspots[0][1], 2)

    def test_circular_dependencies(self):
        self.create_file("a.py", "from .b import b_func\ndef a_func(): b_func()")
        self.create_file("b.py", "from .a import a_func\ndef b_func(): a_func()")

        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        radius_a = analyzer.get_blast_radius("a.a_func")
        self.assertIn("b.b_func", radius_a)

    def test_find_symbol_at_line(self):
        content = "\ndef outer():\n    def inner():\n        pass\n    inner()"
        path = self.create_file("nested.py", content)

        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        # Line 3 is 'def inner():'
        sym = analyzer.graph.find_symbol_at_line(path, 3)
        self.assertIsNotNone(sym)
        self.assertEqual(sym.fqn, "nested.outer.inner")

    def test_malformed_python(self):
        self.create_file("broken.py", "def error(:")
        analyzer = Analyzer(self.src_dir)
        # Should not crash
        analyzer.run()
        self.assertEqual(len(analyzer.graph.symbols), 0)

if __name__ == "__main__":
    unittest.main()