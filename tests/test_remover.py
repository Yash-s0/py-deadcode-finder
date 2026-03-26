import tempfile
import textwrap
import unittest
from pathlib import Path

from deadcode_finder.remover import CodeRemover


class CodeRemoverTests(unittest.TestCase):
    def test_remove_function_matches_exact_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "dup_funcs.py"
            file_path.write_text(
                textwrap.dedent(
                    """\
                    def foo():
                        return 1

                    def foo():
                        return 2
                    """
                ),
                encoding="utf-8",
            )

            remover = CodeRemover(str(root))
            result = remover.remove_function(str(file_path), "foo", 4)

            self.assertEqual(result["status"], "success")
            updated = file_path.read_text(encoding="utf-8")
            self.assertIn("return 1", updated)
            self.assertNotIn("return 2", updated)

    def test_remove_class_matches_exact_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file_path = root / "dup_classes.py"
            file_path.write_text(
                textwrap.dedent(
                    """\
                    class User:
                        pass

                    class User:
                        pass
                    """
                ),
                encoding="utf-8",
            )

            remover = CodeRemover(str(root))
            result = remover.remove_class(str(file_path), "User", 4)

            self.assertEqual(result["status"], "success")
            updated = file_path.read_text(encoding="utf-8")
            self.assertIn("class User:\n    pass", updated)
            self.assertEqual(updated.count("class User"), 1)


if __name__ == "__main__":
    unittest.main()
