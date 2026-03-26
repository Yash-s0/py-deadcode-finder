import tempfile
import textwrap
import unittest
from pathlib import Path

from deadcode_finder.analyzer import DeadCodeAnalyzer


class DeadCodeAnalyzerTests(unittest.TestCase):
    def _analyze(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel_path, content in files.items():
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(textwrap.dedent(content), encoding="utf-8")

            analyzer = DeadCodeAnalyzer(root)
            analyzer.scan()
            report = analyzer.get_report()

            return report, root

    def test_method_call_marks_method_as_used(self):
        report, _ = self._analyze(
            {
                "a.py": """
                class Repo:
                    def save(self):
                        return 1

                def handler():
                    r = Repo()
                    return r.save()
                """
            }
        )

        high_names = {name for _, _, name in report["high_confidence"]["unused_functions"]}
        potential_names = {
            name for _, _, name, _ in report["potentially_used"]["unused_functions"]
        }

        self.assertNotIn("save", high_names)
        self.assertNotIn("save", potential_names)

    def test_duplicate_function_names_are_tracked_per_file(self):
        report, _ = self._analyze(
            {
                "mod1.py": """
                def helper():
                    return 1
                """,
                "mod2.py": """
                def helper():
                    return 2

                print(helper())
                """,
            }
        )

        high_funcs = {
            (Path(file).name, name)
            for file, _line, name in report["high_confidence"]["unused_functions"]
        }

        self.assertIn(("mod1.py", "helper"), high_funcs)
        self.assertNotIn(("mod2.py", "helper"), high_funcs)

    def test_framework_and_all_exports_move_to_potentially_used(self):
        report, _ = self._analyze(
            {
                "svc.py": """
                from fastapi import APIRouter
                from celery import shared_task

                router = APIRouter()

                @router.get('/items')
                def route_fn():
                    return 1

                @shared_task
                def task_fn():
                    return 2

                class User(Base):
                    __tablename__ = 'users'

                def exported_fn():
                    return 3

                __all__ = ['exported_fn', 'User']
                """
            }
        )

        high_func_names = {name for _, _, name in report["high_confidence"]["unused_functions"]}
        potential_func_names = {
            name for _, _, name, _ in report["potentially_used"]["unused_functions"]
        }

        high_class_names = {name for _, _, name in report["high_confidence"]["unused_classes"]}
        potential_class_names = {
            name for _, _, name, _ in report["potentially_used"]["unused_classes"]
        }

        self.assertNotIn("route_fn", high_func_names)
        self.assertNotIn("task_fn", high_func_names)
        self.assertNotIn("exported_fn", high_func_names)
        self.assertIn("route_fn", potential_func_names)
        self.assertIn("task_fn", potential_func_names)
        self.assertIn("exported_fn", potential_func_names)

        self.assertNotIn("User", high_class_names)
        self.assertIn("User", potential_class_names)

    def test_scope_local_variable_detection_with_line_numbers(self):
        report, _ = self._analyze(
            {
                "vars.py": """
                def sample(a, b):
                    used = a
                    unused = 1
                    for i in range(2):
                        loop_var = i
                    with open('x') as fh:
                        pass
                    try:
                        raise ValueError('x')
                    except ValueError as err:
                        pass
                    return used
                """
            }
        )

        file_path, entries = next(iter(report["high_confidence"]["unused_variables"].items()))
        _ = file_path
        by_name = {name: line for line, name in entries}

        self.assertEqual(by_name["unused"], 4)
        self.assertIn("b", by_name)
        self.assertIn("loop_var", by_name)
        self.assertIn("fh", by_name)
        self.assertIn("err", by_name)
        self.assertNotIn("i", by_name)


if __name__ == "__main__":
    unittest.main()
