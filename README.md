# PyDeadCodeFinder

PyDeadCodeFinder is an open-source static-analysis tool for identifying unused Python imports, functions, classes, variables, and unreachable code. It runs entirely on your machine and produces an interactive HTML report that summarizes the results and provides deep links back to the original files.

---

## Key Capabilities

- Project-wide detection of unused imports, functions, classes, and variables.
- Identification of unreachable code segments (for example, statements that follow a `return`).
- Call-graph powered cross-file analysis to reduce false positives.
- Modern HTML report with keyboard shortcuts, filtering, dark mode, and JSON export.
- No external services, agents, or configuration files required.

---

## Requirements

- Python 3.8 or newer
- Linux, macOS, or Windows Subsystem for Linux
- (Recommended) Virtual environment: `python -m venv .venv && source .venv/bin/activate`

---

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/Yash-s0/py-deadcode-finder
cd py-deadcode-finder
pip install -r requirements.txt
```

---

## Usage

Analyze any Python codebase by pointing the CLI at its root directory:

```bash
python cli.py /path/to/project
```

Additional examples:

```bash
# Explicit path
python cli.py /home/user/my-python-project

# Specify a custom output file
python cli.py /home/user/my-python-project --output reports/deadcode.html

# Run against the bundled sample project
python cli.py examples/sample_project
```

The command writes `deadcode_report.html` (or the file supplied via `--output`) to the current working directory.

---

## Report Overview

### Summary dashboard
- Overall “code health” indicator derived from the number of issues detected.
- Counts of files containing unused imports, unused functions, unused classes, unused variables, and unreachable code.

### Detailed sections
1. **Unused Imports** – grouped by file path with per-import line numbers and severity badges.  
2. **Unused Functions** – definitions that are not referenced anywhere in the analyzed project.  
3. **Unused Classes** – class declarations that are never instantiated or referenced.  
4. **Unused Variables** – variables assigned but never read, grouped by file.  
5. **Unreachable Code** – code paths that cannot execute (for example, statements after a `return`).  

### Interactive features
- Keyboard shortcuts (`D` for dark mode, `/` to focus the search box, `?` for the shortcut overlay).
- Responsive layout optimized for desktop and mobile displays.
- Expand/collapse controls for sections with more than ten entries.
- JSON export button for downstream processing.

---

## Design Highlights

- CSS variables power both light and dark themes for consistent theming and easy customization.
- Card-based layout surfaces the most relevant statistics up front.
- Severity colors highlight critical items at a glance.
- All controls degrade gracefully when JavaScript is disabled.

---

## Project Structure

```
py-deadcode-finder/
├── cli.py                      # Command-line interface
├── deadcode_finder/
│   ├── analyzer.py            # Core scanning logic
│   ├── ast_parser.py          # AST parsing helpers
│   ├── call_graph.py          # Call graph builder
│   ├── report.py              # Template rendering
│   └── utils.py               # Shared helpers
├── templates/
│   └── report_template.html   # HTML/CSS template
├── deadcode_report.html       # Example output
├── requirements.txt
└── README.md
```

---

## How It Works

1. **File discovery** – walks the supplied directory, skipping common virtual-environment folders.
2. **AST inspection** – parses each file with Python’s built-in `ast` module to capture imports, definitions, and references.
3. **Call graph assembly** – correlates definitions with their usage across the project.
4. **Issue classification** – determines which constructs are unused or unreachable.
5. **Report rendering** – feeds the collected data to a Jinja2 template to produce the final HTML artifact.

---

## Configuration

The CLI operates with sensible defaults:

- Analyzes every `.py` file beneath the provided path.
- Ignores directories named `env`, `.venv`, or `venv`, as well as `tests`.
- Writes `deadcode_report.html` unless `--output` is provided.

No additional configuration files are necessary.

---

## Use Cases

- Ongoing codebase hygiene and technical-debt reduction.
- Refactoring support: confirm that moved or deprecated APIs are no longer referenced.
- Pre-commit or CI gates that ensure unused artifacts are removed regularly.
- Documentation of unused public APIs before major releases.

---

## Operational Guidance

1. **Review before deletion** – static analysis cannot detect every dynamic code path. Validate findings, especially for public APIs or reflection-heavy modules.
2. **Automate the workflow** – schedule PyDeadCodeFinder in CI so newly introduced dead code is caught early.
3. **Track progress** – export the JSON summary and trend issue counts over time.
4. **Re-run tests** – after removing flagged items, run your test suite to ensure no behavioral regressions were introduced.

---

## Known Limitations

- Dynamic imports, reflection, or runtime metaprogramming may lead to false positives.
- Only Python files are analyzed. Mixed-language projects need separate tooling for other languages.
- Extremely large repositories may benefit from future parallelization or caching improvements.

---

## Contributing

Contributions are welcome. Helpful areas include:

- Reporting bugs or false positives through GitHub issues.
- Improving documentation, examples, or onboarding instructions.
- Enhancing the analyzer (new checks, better heuristics, performance optimizations).
- Integrating the tool with CI pipelines or editor extensions.

For substantial changes, please open an issue to discuss the approach before submitting a pull request.

---

## License

PyDeadCodeFinder is distributed under the MIT License. See `LICENSE` for the full text.

---

## Support

If you encounter a problem or have an enhancement request, open an issue on GitHub. Response times are best-effort based on maintainer availability.
