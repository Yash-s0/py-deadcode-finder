import ast
from pathlib import Path
from deadcode_finder.utils import read_file


class DeadCodeAnalyzer:
    def __init__(self, root):
        self.root = Path(root)
        self.unused_imports = {}
        self.unused_functions = []
        self.unused_classes = []
        self.unused_variables = {}
        self.unreachable_code = {}
        self.function_defs = {}
        self.class_defs = {}
        self.used_names = set()

    def scan(self):
        py_files = [
            p for p in self.root.rglob("*.py")
            if "venv" not in str(p) and ".venv" not in str(p)
            and "env" not in str(p) and "tests" not in str(p)
        ]

        for file in py_files:
            self._analyze_file(file)

        self._compute_dead_functions()
        self._compute_dead_classes()

    def _analyze_file(self, path):
        src = read_file(path)
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return

        visitor = DeadCodeVisitor()
        visitor.visit(tree)

        # Record used names from this file
        self.used_names.update(visitor.used_names)

        # Process imports: keep only those not used in this file
        unused = []
        for imp, lineno in visitor.imports:
            base = imp.split(".")[0]
            if base not in visitor.used_names:
                unused.append((imp, lineno))
        if unused:
            # store as string path for template friendliness
            self.unused_imports[str(path)] = unused

        # Store function/class definitions with the file path and lineno
        for name, (nm, lineno) in visitor.function_defs.items():
            self.function_defs[name] = (str(path), lineno)
        for name, (nm, lineno) in visitor.class_defs.items():
            self.class_defs[name] = (str(path), lineno)

        if visitor.unused_vars:
            self.unused_variables[path] = visitor.unused_vars

        if visitor.unreachable:
            self.unreachable_code[path] = visitor.unreachable

    def _compute_dead_functions(self):
        for name, (file, lineno) in self.function_defs.items():
            if name not in self.used_names:
                self.unused_functions.append((file, lineno, name))

    def _compute_dead_classes(self):
        for name, (file, lineno) in self.class_defs.items():
            if name not in self.used_names:
                self.unused_classes.append((file, lineno, name))

    def get_report(self):
        return {
            "unused_imports": self.unused_imports,
            "unused_functions": self.unused_functions,
            "unused_classes": self.unused_classes,
            "unused_variables": self.unused_variables,
            "unreachable_code": self.unreachable_code
        }


class DeadCodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        self.used_names = set()
        self.function_defs = {}
        self.class_defs = {}
        self.unused_vars = []
        self.unreachable = []
        self.scope = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append((alias.name, node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.imports.append((alias.name, node.lineno))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.function_defs[node.name] = (node.name, node.lineno)
        self.scope.append(set())
        self.generic_visit(node)
        assigned = self.scope.pop()
        unused = assigned - self.used_names
        for v in unused:
            self.unused_vars.append((node.lineno, v))

    def visit_ClassDef(self, node):
        self.class_defs[node.name] = (node.name, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Name):
            if self.scope:
                self.scope[-1].add(node.targets[0].id)
        self.generic_visit(node)

    def visit_Return(self, node):
        self.unreachable.append((node.lineno, "code after return"))
        self.generic_visit(node)
