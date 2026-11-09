import unittest
from unittest.mock import patch
import sys
from io import StringIO
from py_impact.cli import main

class TestCLI(unittest.TestCase):
    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_help(self, mock_stdout):
        with patch('sys.argv', ['py-impact']):
            with self.assertRaises(SystemExit):
                main()
        self.assertIn("usage: py-impact", mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=StringIO)
    def test_cli_invalid_path(self, mock_stdout):
        with patch('sys.argv', ['py-impact', 'orphans', './non_existent_path_xyz']):
            with self.assertRaises(SystemExit):
                main()
        self.assertIn("Error: Path", mock_stdout.getvalue())

if __name__ == "__main__":
    unittest.main()