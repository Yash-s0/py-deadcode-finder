from jinja2 import Template
from pathlib import Path

class ReportGenerator:
    def __init__(self):
        template_path = Path(__file__).parent.parent / "templates" / "report_template.html"
        self.template = Template(template_path.read_text())

    def generate(self, output_file, context):
        html = self.template.render(**context)
        Path(output_file).write_text(html, encoding="utf-8")
        print("[+] Report written to", output_file)
