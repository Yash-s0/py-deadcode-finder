import tempfile
import unittest
from pathlib import Path

from deadcode_finder.report import ReportGenerator


class ReportTemplateTests(unittest.TestCase):
    def test_template_renders_split_confidence_sections(self):
        high_confidence = {
            "unused_imports": {"/tmp/a.py": [("os", 1)]},
            "unused_functions": [("/tmp/a.py", 10, "dead_fn")],
            "unused_classes": [("/tmp/a.py", 20, "DeadClass")],
            "unused_variables": {"/tmp/a.py": [(30, "temp_var")]},
        }

        potentially_used = {
            "unused_imports": {
                "/tmp/b.py": [
                    ("app.workers.celery_worker", 2, "module import may have side effects")
                ]
            },
            "unused_functions": [
                ("/tmp/b.py", 12, "route_fn", "framework route handler")
            ],
            "unused_classes": [
                ("/tmp/b.py", 22, "User", "SQLAlchemy model class")
            ],
            "unused_variables": {
                "/tmp/b.py": [(42, "CONFIG", "module-level variable may be imported externally")]
            },
        }

        counts = {
            "high_confidence": {"imports": 1, "functions": 1, "classes": 1, "variables": 1, "total": 4},
            "potentially_used": {"imports": 1, "functions": 1, "classes": 1, "variables": 1, "total": 4},
            "unreachable": 0,
            "total_findings": 8,
        }

        context = {
            "high_confidence": high_confidence,
            "potentially_used": potentially_used,
            "counts": counts,
            "unused_imports": high_confidence["unused_imports"],
            "unused_functions": high_confidence["unused_functions"],
            "unused_classes": high_confidence["unused_classes"],
            "unused_variables": high_confidence["unused_variables"],
            "unreachable_code": {},
            "health": 88,
            "health_color": "#51cf66",
            "total_issues": 8,
            "generated_at": "Mar 26, 2026 12:00 UTC",
            "server_url": "http://localhost:8765",
        }

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.html"
            ReportGenerator().generate(str(output), context)
            html = output.read_text(encoding="utf-8")

        self.assertIn("High-confidence Unused Imports", html)
        self.assertIn("Potentially Used Imports", html)
        self.assertIn("Potentially Used Functions", html)
        self.assertIn("framework route handler", html)
        self.assertIn("Review manually", html)
        self.assertIn("disabled title=\"Low-confidence finding\"", html)


if __name__ == "__main__":
    unittest.main()
