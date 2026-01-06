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
        self.entry_points = set()  # Track entry points (__main__, test functions, etc.)
        self.decorated_functions = set()  # Track decorated functions
        self.magic_methods = set()  # Track magic methods

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
        self.entry_points.update(visitor.entry_points)
        self.decorated_functions.update(visitor.decorated_functions)

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
            self.unused_variables[str(path)] = visitor.unused_vars

        if visitor.unreachable:
            self.unreachable_code[str(path)] = visitor.unreachable

    def _compute_dead_functions(self):
        magic_methods = {'__init__', '__str__', '__repr__', '__eq__', '__hash__', 
                        '__lt__', '__le__', '__gt__', '__ge__', '__len__', '__getitem__',
                        '__setitem__', '__delitem__', '__iter__', '__next__', '__contains__',
                        '__enter__', '__exit__', '__call__', '__new__', '__del__'}
        
        for name, (file, lineno) in self.function_defs.items():
            # Skip if used, is an entry point, decorated, or magic method
            if (name not in self.used_names and 
                name not in self.entry_points and
                name not in self.decorated_functions and
                name not in magic_methods):
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
        self.entry_points = set()
        self.decorated_functions = set()
        self.in_function = False
        self.after_return = False

    def visit_Import(self, node):
        for alias in node.names:
            # Use the alias if present, otherwise use the import name
            name_used = alias.asname if alias.asname else alias.name
            self.imports.append((name_used, node.lineno))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            # Use the alias if present, otherwise use the import name
            name_used = alias.asname if alias.asname else alias.name
            self.imports.append((name_used, node.lineno))
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Check for decorators
        if node.decorator_list:
            self.decorated_functions.add(node.name)
            # Track decorator names as used
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    self.used_names.add(decorator.id)
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    self.used_names.add(decorator.func.id)
        
        # Check for entry points
        if node.name in ('main', 'run', 'execute'):
            self.entry_points.add(node.name)
        # Check for test functions
        if node.name.startswith('test_'):
            self.entry_points.add(node.name)
            
        self.function_defs[node.name] = (node.name, node.lineno)
        self.scope.append(set())
        old_in_function = self.in_function
        old_after_return = self.after_return
        self.in_function = True
        self.after_return = False
        
        self.generic_visit(node)
        
        self.in_function = old_in_function
        self.after_return = old_after_return
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
        if self.in_function:
            self.after_return = True
        self.generic_visit(node)

    def visit_stmt_after_return(self, node):
        """Helper to detect unreachable code after return"""
        if self.after_return and self.in_function:
            if not isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Return)):
                self.unreachable.append((node.lineno, "code after return"))
        return node

    def visit_If(self, node):
        """Check for __main__ entry point"""
        if isinstance(node.test, ast.Compare):
            if (isinstance(node.test.left, ast.Name) and 
                node.test.left.id == '__name__' and
                any(isinstance(comp, ast.Constant) and comp.value == '__main__' 
                    for comp in node.test.comparators)):
                # Mark functions called in __main__ as entry points
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        self.entry_points.add(child.func.id)
        self.generic_visit(node)
