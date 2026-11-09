import unittest
import tempfile
import shutil
from pathlib import Path
from py_impact.analyzer import Analyzer

class TestResolution(unittest.TestCase):
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

    def test_class_self_resolution(self):
        # Fix MAJOR linker issue: self.method() calls
        content = """
class Worker:
    def step1(self):
        pass
    def step2(self):
        self.step1()
"""
        self.create_file("work.py", content)
        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        self.assertIn("work.Worker.step1", analyzer.graph.incoming)
        self.assertIn("work.Worker.step2", analyzer.graph.incoming["work.Worker.step1"])

    def test_orphan_entry_point_filtering(self):
        # Fix MAJOR analyzer issue: __init__ and main should not be orphans
        self.create_file("app.py", "def main(): pass\ndef other(): pass")
        self.create_file("pkg/__init__.py", "def setup(): pass")
        
        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        orphans = [o.name for o in analyzer.get_orphans()]
        self.assertIn("other", orphans)
        self.assertNotIn("main", orphans)
        self.assertNotIn("setup", orphans) # setup is in __init__.py, but sym name is setup.
        # Let's check name filter explicitly
        self.assertNotIn("__init__", [o.name for o in analyzer.get_orphans()])

    def test_deep_package_root_detection(self):
        # Fix MINOR parser issue: package root detection
        (self.src_dir / "my_proj").mkdir()
        self.create_file("my_proj/__init__.py", "")
        self.create_file("my_proj/utils.py", "def tool(): pass")
        self.create_file("my_proj/main.py", "from .utils import tool\ndef run(): tool()")
        
        # Run analysis on a subdirectory
        analyzer = Analyzer(self.src_dir / "my_proj")
        analyzer.run()
        
        # Root should be detected as self.src_dir, FQNs should start with my_proj
        self.assertIn("my_proj.utils.tool", analyzer.graph.symbols)
        self.assertIn("my_proj.main.run", analyzer.graph.incoming["my_proj.utils.tool"])

    def test_iterative_formatter_limit(self):
        # Fix MINOR formatter issue: unbounded recursion
        # Create a deep call chain
        code = []
        for i in range(2000): # Exceeds default recursion limit (usually 1000)
            code.append(f"def f{i}(): f{i+1}()")
        code.append("def f2000(): pass")
        self.create_file("deep.py", "\n".join(code))
        
        analyzer = Analyzer(self.src_dir)
        analyzer.run()
        
        from py_impact.formatter import format_tree
        # Should not crash
        output = format_tree(analyzer.graph, "deep.f2000")
        self.assertIn("deep.f0", output)

if __name__ == "__main__":
    unittest.main()