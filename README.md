# PyDeadCodeFinder 🧹

A fast, local static analyzer that detects unused code in Python projects. No external services, no configuration required. Just run it and get a beautiful, interactive HTML report.

**Perfect for cleaning up dead code, optimizing imports, and maintaining code health! 🚀**

---

## ✨ Features

- 🔍 **Unused Imports Detection** - Find all unused imports across your project
- ⚙️ **Unused Functions** - Identify functions that are never called
- 🏗️ **Unused Classes** - Discover unused class definitions
- 📊 **Unused Variables** - Find unused variable assignments
- 🚫 **Unreachable Code** - Detect dead code after return statements
- 📁 **Local Analysis** - No external services, everything runs on your machine
- ⚡ **Lightning Fast** - Quickly analyzes your entire project
- 🎨 **Beautiful Reports** - Interactive HTML reports with detailed statistics
- 📥 **Export Functionality** - Export reports as JSON for further processing

---

## ✅ Requirements

- Python 3.8 or newer
- Runs on Linux, macOS, and WSL (Windows) terminals
- Recommended: a virtual environment (`python -m venv .venv && source .venv/bin/activate`)

---

## 🚀 Installation

### Clone the repository
```bash
git clone https://github.com/Yash-s0/py-deadcode-finder
cd py-deadcode-finder
```

### Install dependencies
```bash
pip install -r requirements.txt
```

---

## 📖 Usage

### Basic Usage
```bash
python cli.py /path/to/your/project
```

### Example
```bash
python cli.py /home/user/my-python-project
```

### Custom Output Path
```bash
python cli.py /home/user/my-python-project --output reports/deadcode.html
```

### Try the bundled sample project
```bash
python cli.py examples/sample_project
```

The tool will analyze your project and generate a beautiful HTML report named `deadcode_report.html` in the current directory.

---

## 📊 Report Features

The generated HTML report includes:

### 🎯 Summary Dashboard
- Quick overview of all detected issues
- Statistics for each category
- Total count of problems found

### 📋 Detailed Sections

1. **Unused Imports**
   - Shows all unused import statements
   - Grouped by file
   - Line numbers for easy navigation
   - Color-coded severity indicators

2. **Unused Functions**
   - Lists all detected unused functions
   - File location and line numbers
   - Quick reference for each function

3. **Unused Classes**
   - Classes that are defined but never instantiated
   - Complete file paths and line numbers

4. **Unused Variables**
   - Variable assignments that are never used
   - Grouped by file for organization

5. **Unreachable Code**
   - Code that cannot be executed
   - Typically found after return statements
   - Critical for code cleanup

### 🎁 Interactive Features

- **View More/Less Toggle** - Sections with more than 10 items automatically collapse with "View More" buttons
- **Beautiful UI** - Modern gradient design with smooth animations
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **Dark Mode Toggle** - Press `D` (or use the floating button) to switch themes; the preference persists and respects your OS default
- **Keyboard Shortcuts** - Press `?` anywhere in the report to surface all hotkeys
- **Export to JSON** - Download your report in JSON format for programmatic access
- **Color-Coded Severity** - Visual indicators for issue severity
- **Smooth Animations** - Professional transitions and interactions

---

## 🎨 Report Design Highlights

- **Modern Gradient Theme** - Professional purple gradient background
- **Card-Based Layout** - Clean, organized sections
- **Summary Statistics** - Quick overview at a glance
- **Issue Badges** - Visual indicators for problem counts
- **Hover Effects** - Interactive elements respond to user interaction
- **Mobile Friendly** - Fully responsive design
- **CSS Variables** - One stylesheet powers both light and dark modes, so custom theming is straightforward

---

## 📁 Project Structure

```
py-deadcode-finder/
├── cli.py                      # Command-line interface
├── deadcode_finder/
│   ├── __init__.py
│   ├── analyzer.py            # Main analysis engine
│   ├── ast_parser.py          # AST parsing logic
│   ├── call_graph.py          # Call graph analysis
│   ├── report.py              # Report generation
│   └── utils.py               # Utility functions
├── templates/
│   └── report_template.html   # HTML report template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## 🔍 How It Works

1. **AST Analysis** - Uses Python's Abstract Syntax Tree (AST) to understand code structure
2. **Call Graph Building** - Builds a graph of function calls and class instantiations
3. **Dead Code Detection** - Compares definitions with actual usage
4. **Report Generation** - Creates a beautiful, interactive HTML report

---

## ⚙️ Configuration

No configuration needed! Just run the analyzer on your project directory and it will automatically detect all Python files.

**Supported:**
- Regular Python files (.py)
- Multi-file projects
- Nested directories
- Local modules

---

## 🎯 Use Cases

- **Code Cleanup** - Remove unused code to reduce technical debt
- **Optimization** - Identify unnecessary imports and dependencies
- **Refactoring** - Find dead code during refactoring sessions
- **Code Review** - Use reports as part of code review process
- **CI/CD Integration** - Run as part of your development pipeline
- **Learning** - Understand code usage patterns in existing projects

---

## 💡 Tips & Best Practices

1. **Review Carefully** - Some unused code might be part of your public API
2. **Run Regularly** - Include in your CI/CD pipeline
3. **Export Reports** - Keep records of analysis over time
4. **Share Reports** - Use HTML reports in code review discussions
5. **Iterate** - Run multiple times as you clean up code

---

## ⚠️ Important Notes

- The tool performs **static analysis** and may have false positives
- Code used via reflection or dynamic imports may appear unused
- Always review findings before deleting code
- Test thoroughly after removing flagged code

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest improvements
- Submit pull requests
- Share your feedback

---

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🙏 Acknowledgments

Built with Python's AST module for powerful code analysis.

---

## 📞 Support

For issues, questions, or suggestions, please create an issue on GitHub.

**Happy code cleaning! 🎉**
