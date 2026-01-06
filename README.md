# py-deadcode-finder

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Dead code detection for Python projects with interactive removal capabilities.  
[Features](#-features) • [Quick Start](#-quick-start) • [Usage](#usage) • [Report](#-report-features) • [Contributing](#-contributing) • [License](#-license)

</div>

---

## ✨ Features

### 🔎 Advanced Code Analysis
- **Unused Imports** – file-scoped reports with line numbers.
- **Unused Functions & Classes** – cross-project call graph with smart detection.
- **Decorator Detection** – recognizes decorated functions (e.g., @property, @staticmethod).
- **Magic Method Recognition** – excludes __init__, __str__, and other special methods.
- **Entry Point Detection** – identifies main(), test functions, and __main__ blocks.
- **Unused Variables** – highlights assignments that are never read.
- **Unreachable Code** – detects code after `return`, `raise`, or similar exits.
- **Health Score** – single metric summarizing the overall findings.

### 🎨 Interactive Report
- **One-Click Removal** – Remove dead code directly from the HTML report.
- **Undo Functionality** – Revert removals with automatic backups (Ctrl+Z).
- **Real-time Updates** – Watch counts update as you clean your code.
- **Server Status** – Visual indicator showing removal server availability.
- Responsive layout with light/dark themes and keyboard shortcuts.
- Global search (`/`) with live filtering across every issue.
- Collapsible sections for large result sets plus JSON export.
- All CSS and JS inline—no external network calls.

### 🛠️ Code Removal Features
- **Safe Removal** – Automatic backups before any modification.
- **Granular Control** – Remove individual imports, functions, or classes.
- **Backup Management** – All backups stored in `.deadcode_backups/` folder.
- **Confirmation Prompts** – Prevents accidental deletions.
- **Visual Feedback** – Smooth animations and notifications for all actions.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or newer

### Installation

```bash
git clone https://github.com/Yash-s0/py-deadcode-finder
cd py-deadcode-finder
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
```

### Basic run

```bash
# Generate report only (no removal server)
python cli.py /path/to/project --no-server

# Generate report with interactive removal (default)
python cli.py /path/to/project

# Custom output file and port
python cli.py /path/to/project --output my_report.html --port 8080
```

The tool will:
1. Scan your project for dead code
2. Start a removal server (unless `--no-server` is specified)
3. Generate an interactive HTML report
4. Keep running to handle removal requests (press Ctrl+C to stop)

**Important:** Keep the terminal running if you want to use the removal features in the HTML report.

The command generates `deadcode_report.html` in the current directory.

---

## Usage

```bash
python cli.py [path] [options]

Arguments:
  path              Target directory (default: current working directory)

Options:
  --output, -o      Destination HTML file (default: deadcode_report.html)
```

Examples:

```bash
# Analyze explicit path
python cli.py /home/user/service

# Customize the output location
python cli.py . --output reports/deadcode.html

# Try the bundled sample
python cli.py examples/sample_project
```

---

## 📊 Report Features

### Summary dashboard
- Code health gauge
- Counts of unused imports, functions, classes, variables
- Unreachable code file tally

### Detailed sections
- **Unused Imports**: grouped by file with severity accents.
- **Unused Functions & Classes**: includes line numbers and file hyperlinks.
- **Unused Variables**: per-file grids, ideal for internal refactors.
- **Unreachable Code**: surfaces dead logic to simplify control flow.

### Interactive elements
- Keyboard shortcuts (`D`, `/`, `?`)
- Search results banner and per-item highlighting
- JSON export button for downstream processing
- Print-friendly layout that hides controls

---

## 📁 Project Layout

```
py-deadcode-finder/
├── cli.py                   # CLI entry point
├── deadcode_finder/
│   ├── analyzer.py         # Scanning + AST orchestration
│   ├── call_graph.py       # Call graph utilities
│   ├── report.py           # Jinja2 rendering
│   └── utils.py            # Shared helpers
├── templates/
│   └── report_template.html
├── deadcode_report.html    # Sample output
└── README.md
```

---

## ⚙️ How It Works

1. Recursively discovers `.py` files (skipping common virtual env folders).
2. Parses each file’s AST to track imports, definitions, and references.
3. Builds a project-wide call graph to correlate usage.
4. Classifies code as unused or unreachable based on collected evidence.
5. Renders the aggregated data into a single-page HTML report via Jinja2.

---

## 🧩 Configuration Defaults

- No configuration file required.
- Ignores `env`, `.venv`, `venv`, and `tests` directories by default.
- Writes `deadcode_report.html` unless `--output` is provided.

---

## 🎯 Use Cases

- Routine codebase hygiene and technical-debt reduction.
- Pre-release sweeps to ensure public APIs remain purposeful.
- CI integration to prevent dead code from accumulating.
- Documentation aid when auditing legacy projects.

---

## ⚠️ Limitations

- Static analysis cannot observe reflection, dynamic imports, or runtime metaprogramming—manual review is recommended before deleting flagged code.
- Currently targets Python only; polyglot repositories require additional tooling.
- Very large monorepos may need caching/parallelism (future enhancement).

---

## 🤝 Contributing

Contributions of all sizes are welcome:

1. Fork the repository and create a feature branch.
2. Implement your change following PEP 8 (Black formatting preferred).
3. Add/adjust tests or sample data if relevant.
4. Open a pull request describing the motivation and approach.

Bug reports, feature ideas, and UX suggestions can be filed through GitHub Issues.

---

## 📝 License

Released under the MIT License. See [LICENSE](LICENSE) for details.

---

## 📞 Support

Encountered a bug or have a question? Please [open an issue](https://github.com/Yash-s0/py-deadcode-finder/issues). Response times are best-effort based on maintainer availability.

<div align="center">

**⭐ If this project helps you, consider starring the repository! ⭐**

</div>
