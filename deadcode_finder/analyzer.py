import ast
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

from deadcode_finder.utils import read_file


MAGIC_METHODS = {
    "__init__", "__str__", "__repr__", "__eq__", "__hash__", "__lt__", "__le__",
    "__gt__", "__ge__", "__len__", "__getitem__", "__setitem__", "__delitem__",
    "__iter__", "__next__", "__contains__", "__enter__", "__exit__", "__call__",
    "__new__", "__del__", "__getattr__", "__getattribute__", "__setattr__",
}

ROUTE_DECORATOR_NAMES = {
    "route", "get", "post", "put", "delete", "patch", "options", "head", "websocket"
}

SQLALCHEMY_BASE_NAMES = {
    "Base", "Model", "DeclarativeBase"
}

ENTRYPOINT_NAMES = {
    "main", "run", "execute"
}


@dataclass
class Symbol:
    symbol_id: str
    kind: str
    module: str
    qualname: str
    name: str
    file: str
    line: int
    is_method: bool = False
    class_symbol_id: Optional[str] = None
    reasons: Set[str] = field(default_factory=set)


@dataclass
class ImportBinding:
    symbol_id: str
    module: str
    file: str
    line: int
    bound_name: str
    report_name: str
    imported_module: str
    imported_name: Optional[str]
    has_alias: bool
    is_star: bool = False
    reasons: Set[str] = field(default_factory=set)
    target_symbol_ids: Set[str] = field(default_factory=set)


@dataclass
class ModuleInfo:
    file_path: Path
    file_str: str
    module: str
    package: str
    tree: ast.AST
    exports: Set[str] = field(default_factory=set)
    import_ids: List[str] = field(default_factory=list)
    import_bindings_by_name: DefaultDict[str, List[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    module_aliases: DefaultDict[str, Set[str]] = field(
        default_factory=lambda: defaultdict(set)
    )


class ScopeState:
    def __init__(self, kind: str):
        self.kind = kind
        self.assigned: Dict[str, int] = {}
        self.used: Set[str] = set()
        self.inferred_types: Dict[str, Set[str]] = {}
        self.global_names: Set[str] = set()
        self.nonlocal_names: Set[str] = set()


class DeadCodeAnalyzer:
    def __init__(self, root):
        self.root = Path(root)

        self.modules: Dict[str, ModuleInfo] = {}

        self.symbols: Dict[str, Symbol] = {}
        self.function_symbols: Dict[str, Symbol] = {}
        self.class_symbols: Dict[str, Symbol] = {}
        self.import_bindings: Dict[str, ImportBinding] = {}

        self.top_level_defs_by_module: DefaultDict[str, DefaultDict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.symbol_ids_by_module_and_name: DefaultDict[str, DefaultDict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.function_ids_by_name: DefaultDict[str, Set[str]] = defaultdict(set)
        self.method_ids_by_name: DefaultDict[str, Set[str]] = defaultdict(set)
        self.class_methods: DefaultDict[str, DefaultDict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

        self.function_lookup: Dict[Tuple[str, str, int], str] = {}
        self.class_lookup: Dict[Tuple[str, str, int], str] = {}

        self.used_symbol_ids: Set[str] = set()
        self.used_import_ids: Set[str] = set()
        self.potential_symbol_reasons: DefaultDict[str, Set[str]] = defaultdict(set)

        self.unreachable_code: Dict[str, List[Tuple[int, str]]] = {}

        self._high_confidence: Dict[str, object] = {}
        self._potentially_used: Dict[str, object] = {}
        self._counts: Dict[str, object] = {}

    def scan(self):
        self._reset_runtime_results()

        py_files = [
            p for p in self.root.rglob("*.py")
            if "venv" not in str(p)
            and ".venv" not in str(p)
            and "env" not in str(p)
            and "tests" not in str(p)
        ]

        for file_path in sorted(py_files):
            src = read_file(file_path)
            try:
                tree = ast.parse(src, filename=str(file_path))
            except SyntaxError:
                continue

            module_name = self._module_name_from_path(file_path)
            package_name = self._package_name(module_name, file_path)

            module_info = ModuleInfo(
                file_path=file_path,
                file_str=str(file_path),
                module=module_name,
                package=package_name,
                tree=tree,
            )
            self.modules[module_name] = module_info

            collector = DefinitionCollector(self, module_info)
            collector.visit(tree)

        self._apply_export_reasons()
        self._resolve_import_targets()

        high_unused_variables: DefaultDict[str, List[Tuple[int, str]]] = defaultdict(list)
        potential_unused_variables: DefaultDict[str, List[Tuple[int, str, str]]] = defaultdict(list)

        for module_name in sorted(self.modules):
            module_info = self.modules[module_name]
            ref_collector = ReferenceCollector(self, module_info)
            ref_collector.visit(module_info.tree)

            self.used_symbol_ids.update(ref_collector.used_symbol_ids)
            self.used_import_ids.update(ref_collector.used_import_ids)

            for symbol_id, reasons in ref_collector.potential_symbol_reasons.items():
                self.potential_symbol_reasons[symbol_id].update(reasons)

            if ref_collector.unused_variables_high:
                high_unused_variables[module_info.file_str].extend(
                    ref_collector.unused_variables_high
                )
            if ref_collector.unused_variables_potential:
                potential_unused_variables[module_info.file_str].extend(
                    ref_collector.unused_variables_potential
                )
            if ref_collector.unreachable:
                self.unreachable_code[module_info.file_str] = sorted(
                    ref_collector.unreachable,
                    key=lambda item: (item[0], item[1]),
                )

        self._classify_findings(high_unused_variables, potential_unused_variables)

    def get_report(self):
        high_confidence = self._high_confidence
        potentially_used = self._potentially_used

        return {
            "high_confidence": high_confidence,
            "potentially_used": potentially_used,
            "counts": self._counts,
            "unused_imports": high_confidence["unused_imports"],
            "unused_functions": high_confidence["unused_functions"],
            "unused_classes": high_confidence["unused_classes"],
            "unused_variables": high_confidence["unused_variables"],
            "unreachable_code": self.unreachable_code,
        }

    def _reset_runtime_results(self):
        self.modules = {}
        self.symbols = {}
        self.function_symbols = {}
        self.class_symbols = {}
        self.import_bindings = {}
        self.top_level_defs_by_module = defaultdict(lambda: defaultdict(set))
        self.symbol_ids_by_module_and_name = defaultdict(lambda: defaultdict(set))
        self.function_ids_by_name = defaultdict(set)
        self.method_ids_by_name = defaultdict(set)
        self.class_methods = defaultdict(lambda: defaultdict(set))
        self.function_lookup = {}
        self.class_lookup = {}

        self.used_symbol_ids.clear()
        self.used_import_ids.clear()
        self.potential_symbol_reasons.clear()
        self.unreachable_code = {}
        self._high_confidence = {}
        self._potentially_used = {}
        self._counts = {}

    def _module_name_from_path(self, file_path: Path) -> str:
        rel = file_path.relative_to(self.root)
        parts = list(rel.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else "__root__"

    def _package_name(self, module_name: str, file_path: Path) -> str:
        if file_path.name == "__init__.py":
            return module_name
        if "." not in module_name:
            return ""
        return module_name.rsplit(".", 1)[0]

    def _build_symbol_id(self, module: str, kind: str, qualname: str, line: int) -> str:
        return "{}|{}|{}|{}".format(module, kind, qualname, line)

    def _register_symbol(self, symbol: Symbol, top_level: bool = False):
        self.symbols[symbol.symbol_id] = symbol

        if symbol.kind == "function":
            self.function_symbols[symbol.symbol_id] = symbol
            self.function_ids_by_name[symbol.name].add(symbol.symbol_id)
            self.function_lookup[(symbol.module, symbol.qualname, symbol.line)] = symbol.symbol_id
            if symbol.is_method:
                self.method_ids_by_name[symbol.name].add(symbol.symbol_id)
                if symbol.class_symbol_id:
                    self.class_methods[symbol.class_symbol_id][symbol.name].add(symbol.symbol_id)

        elif symbol.kind == "class":
            self.class_symbols[symbol.symbol_id] = symbol
            self.class_lookup[(symbol.module, symbol.qualname, symbol.line)] = symbol.symbol_id

        self.symbol_ids_by_module_and_name[symbol.module][symbol.name].add(symbol.symbol_id)

        if top_level:
            self.top_level_defs_by_module[symbol.module][symbol.name].add(symbol.symbol_id)

    def _register_import(self, binding: ImportBinding, module_info: ModuleInfo):
        self.import_bindings[binding.symbol_id] = binding
        module_info.import_ids.append(binding.symbol_id)
        module_info.import_bindings_by_name[binding.bound_name].append(binding.symbol_id)

        if binding.imported_name is None:
            module_info.module_aliases[binding.bound_name].add(binding.imported_module)

    def _apply_export_reasons(self):
        for module_name, module_info in self.modules.items():
            if not module_info.exports:
                continue

            for exported_name in module_info.exports:
                for symbol_id in self.top_level_defs_by_module[module_name].get(exported_name, set()):
                    self.symbols[symbol_id].reasons.add("exported_in___all__")

                for import_id in module_info.import_bindings_by_name.get(exported_name, []):
                    self.import_bindings[import_id].reasons.add("exported_in___all__")

    def _resolve_import_targets(self):
        for binding in self.import_bindings.values():
            if binding.is_star:
                binding.reasons.add("star_import")
                continue

            if binding.imported_name:
                target_ids = self.top_level_defs_by_module[binding.imported_module].get(
                    binding.imported_name,
                    set(),
                )
                if target_ids:
                    binding.target_symbol_ids.update(target_ids)

            if binding.imported_name is None and not binding.has_alias:
                binding.reasons.add("module_import_side_effect")

    def _classify_findings(
        self,
        high_unused_variables: Dict[str, List[Tuple[int, str]]],
        potential_unused_variables: Dict[str, List[Tuple[int, str, str]]],
    ):
        high_imports: DefaultDict[str, List[Tuple[str, int]]] = defaultdict(list)
        potential_imports: DefaultDict[str, List[Tuple[str, int, str]]] = defaultdict(list)

        for binding in self.import_bindings.values():
            if binding.symbol_id in self.used_import_ids:
                continue

            reason_codes = set(binding.reasons)
            if binding.target_symbol_ids:
                # If import points to project symbols and none are used, keep normal flow.
                pass

            if reason_codes:
                reason = self._format_reasons(reason_codes)
                potential_imports[binding.file].append((binding.report_name, binding.line, reason))
            else:
                high_imports[binding.file].append((binding.report_name, binding.line))

        high_functions: List[Tuple[str, int, str]] = []
        potential_functions: List[Tuple[str, int, str, str]] = []

        for symbol in self.function_symbols.values():
            if symbol.name in MAGIC_METHODS:
                continue

            if symbol.symbol_id in self.used_symbol_ids:
                continue

            reason_codes = set(symbol.reasons)
            reason_codes.update(self.potential_symbol_reasons.get(symbol.symbol_id, set()))

            if symbol.is_method and symbol.class_symbol_id:
                class_symbol = self.class_symbols.get(symbol.class_symbol_id)
                if class_symbol and class_symbol.reasons:
                    reason_codes.add("method_on_framework_class")

            item = (symbol.file, symbol.line, symbol.name)
            if reason_codes:
                potential_functions.append(item + (self._format_reasons(reason_codes),))
            else:
                high_functions.append(item)

        high_classes: List[Tuple[str, int, str]] = []
        potential_classes: List[Tuple[str, int, str, str]] = []

        for symbol in self.class_symbols.values():
            if symbol.symbol_id in self.used_symbol_ids:
                continue

            reason_codes = set(symbol.reasons)
            reason_codes.update(self.potential_symbol_reasons.get(symbol.symbol_id, set()))

            item = (symbol.file, symbol.line, symbol.name)
            if reason_codes:
                potential_classes.append(item + (self._format_reasons(reason_codes),))
            else:
                high_classes.append(item)

        high_variables: DefaultDict[str, List[Tuple[int, str]]] = defaultdict(list)
        potential_variables: DefaultDict[str, List[Tuple[int, str, str]]] = defaultdict(list)

        for file_path, items in high_unused_variables.items():
            high_variables[file_path].extend(sorted(items, key=lambda item: (item[0], item[1])))

        for file_path, items in potential_unused_variables.items():
            potential_variables[file_path].extend(sorted(items, key=lambda item: (item[0], item[1])))

        for file_path in list(high_imports):
            high_imports[file_path] = sorted(high_imports[file_path], key=lambda item: (item[1], item[0]))
        for file_path in list(potential_imports):
            potential_imports[file_path] = sorted(
                potential_imports[file_path], key=lambda item: (item[1], item[0])
            )

        high_functions = sorted(high_functions, key=lambda item: (item[0], item[1], item[2]))
        potential_functions = sorted(
            potential_functions,
            key=lambda item: (item[0], item[1], item[2]),
        )

        high_classes = sorted(high_classes, key=lambda item: (item[0], item[1], item[2]))
        potential_classes = sorted(
            potential_classes,
            key=lambda item: (item[0], item[1], item[2]),
        )

        high_confidence = {
            "unused_imports": dict(sorted(high_imports.items())),
            "unused_functions": high_functions,
            "unused_classes": high_classes,
            "unused_variables": dict(sorted(high_variables.items())),
        }

        potentially_used = {
            "unused_imports": dict(sorted(potential_imports.items())),
            "unused_functions": potential_functions,
            "unused_classes": potential_classes,
            "unused_variables": dict(sorted(potential_variables.items())),
        }

        high_counts = {
            "imports": sum(len(items) for items in high_confidence["unused_imports"].values()),
            "functions": len(high_confidence["unused_functions"]),
            "classes": len(high_confidence["unused_classes"]),
            "variables": sum(len(items) for items in high_confidence["unused_variables"].values()),
        }
        high_counts["total"] = sum(high_counts.values())

        potential_counts = {
            "imports": sum(len(items) for items in potentially_used["unused_imports"].values()),
            "functions": len(potentially_used["unused_functions"]),
            "classes": len(potentially_used["unused_classes"]),
            "variables": sum(len(items) for items in potentially_used["unused_variables"].values()),
        }
        potential_counts["total"] = sum(potential_counts.values())

        unreachable_count = sum(len(items) for items in self.unreachable_code.values())

        self._high_confidence = high_confidence
        self._potentially_used = potentially_used
        self._counts = {
            "high_confidence": high_counts,
            "potentially_used": potential_counts,
            "unreachable": unreachable_count,
            "total_findings": high_counts["total"] + potential_counts["total"] + unreachable_count,
        }

    def _format_reasons(self, reason_codes: Iterable[str]) -> str:
        labels = {
            "decorated_function": "decorated function",
            "framework_route_handler": "framework route handler",
            "celery_task": "Celery task",
            "sqlalchemy_model_class": "SQLAlchemy model class",
            "exported_in___all__": "exported via __all__",
            "common_entrypoint_name": "common entry point name",
            "star_import": "star import",
            "module_import_side_effect": "module import may have side effects",
            "method_on_framework_class": "method on framework-managed class",
            "unresolved_attribute_call": "matched unresolved attribute call",
            "unresolved_attribute_access": "matched unresolved attribute access",
            "module_level_variable": "module-level variable may be imported externally",
        }
        normalized = sorted(set(reason_codes))
        return ", ".join(labels.get(code, code) for code in normalized)


class DefinitionCollector(ast.NodeVisitor):
    def __init__(self, analyzer: DeadCodeAnalyzer, module_info: ModuleInfo):
        self.analyzer = analyzer
        self.module_info = module_info
        self.qualname_stack: List[str] = []
        self.container_stack: List[str] = []
        self.class_symbol_stack: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            bound_name = alias.asname if alias.asname else alias.name.split(".")[0]
            report_name = alias.asname if alias.asname else alias.name
            symbol_id = self.analyzer._build_symbol_id(
                self.module_info.module,
                "import",
                "{}:{}".format(report_name, node.lineno),
                node.lineno,
            )

            binding = ImportBinding(
                symbol_id=symbol_id,
                module=self.module_info.module,
                file=self.module_info.file_str,
                line=node.lineno,
                bound_name=bound_name,
                report_name=report_name,
                imported_module=alias.name,
                imported_name=None,
                has_alias=bool(alias.asname),
                is_star=False,
            )
            self.analyzer._register_import(binding, self.module_info)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        resolved_module = _resolve_import_from_module(
            self.module_info.package,
            node.level,
            node.module,
        )

        for alias in node.names:
            is_star = alias.name == "*"
            bound_name = alias.asname if alias.asname else alias.name
            report_name = alias.asname if alias.asname else alias.name

            symbol_id = self.analyzer._build_symbol_id(
                self.module_info.module,
                "import",
                "{}:{}".format(report_name, node.lineno),
                node.lineno,
            )

            binding = ImportBinding(
                symbol_id=symbol_id,
                module=self.module_info.module,
                file=self.module_info.file_str,
                line=node.lineno,
                bound_name=bound_name,
                report_name=report_name,
                imported_module=resolved_module,
                imported_name=None if is_star else alias.name,
                has_alias=bool(alias.asname),
                is_star=is_star,
            )
            self.analyzer._register_import(binding, self.module_info)

    def visit_Assign(self, node: ast.Assign):
        if not self.container_stack:
            self._collect_module_exports(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if not self.container_stack:
            self._collect_module_exports([node.target], node.value)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        if not self.container_stack and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            values = _extract_string_constants(node.value)
            if values:
                self.module_info.exports.update(values)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def _visit_function(self, node):
        qualname = ".".join(self.qualname_stack + [node.name]) if self.qualname_stack else node.name
        is_method = bool(self.container_stack and self.container_stack[-1] == "class")
        class_symbol_id = self.class_symbol_stack[-1] if is_method and self.class_symbol_stack else None

        symbol_id = self.analyzer._build_symbol_id(
            self.module_info.module,
            "function",
            qualname,
            node.lineno,
        )
        symbol = Symbol(
            symbol_id=symbol_id,
            kind="function",
            module=self.module_info.module,
            qualname=qualname,
            name=node.name,
            file=self.module_info.file_str,
            line=node.lineno,
            is_method=is_method,
            class_symbol_id=class_symbol_id,
        )

        if node.name in ENTRYPOINT_NAMES or node.name.startswith("test_"):
            symbol.reasons.add("common_entrypoint_name")

        decorator_names = [_decorator_name(decorator) for decorator in node.decorator_list]
        if decorator_names:
            symbol.reasons.add("decorated_function")
            for decorator in decorator_names:
                tail = decorator.split(".")[-1]
                if tail in ROUTE_DECORATOR_NAMES:
                    symbol.reasons.add("framework_route_handler")
                if tail == "task" or decorator == "shared_task":
                    symbol.reasons.add("celery_task")

        top_level = not self.container_stack
        self.analyzer._register_symbol(symbol, top_level=top_level)

        self.qualname_stack.append(node.name)
        self.container_stack.append("function")
        self.generic_visit(node)
        self.container_stack.pop()
        self.qualname_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        qualname = ".".join(self.qualname_stack + [node.name]) if self.qualname_stack else node.name

        symbol_id = self.analyzer._build_symbol_id(
            self.module_info.module,
            "class",
            qualname,
            node.lineno,
        )
        symbol = Symbol(
            symbol_id=symbol_id,
            kind="class",
            module=self.module_info.module,
            qualname=qualname,
            name=node.name,
            file=self.module_info.file_str,
            line=node.lineno,
        )

        if _is_sqlalchemy_model_class(node):
            symbol.reasons.add("sqlalchemy_model_class")

        top_level = not self.container_stack
        self.analyzer._register_symbol(symbol, top_level=top_level)

        self.qualname_stack.append(node.name)
        self.container_stack.append("class")
        self.class_symbol_stack.append(symbol_id)

        self.generic_visit(node)

        self.class_symbol_stack.pop()
        self.container_stack.pop()
        self.qualname_stack.pop()

    def _collect_module_exports(self, targets: List[ast.AST], value: Optional[ast.AST]):
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                values = _extract_string_constants(value)
                if values:
                    self.module_info.exports.update(values)


class ReferenceCollector(ast.NodeVisitor):
    def __init__(self, analyzer: DeadCodeAnalyzer, module_info: ModuleInfo):
        self.analyzer = analyzer
        self.module_info = module_info

        self.used_symbol_ids: Set[str] = set()
        self.used_import_ids: Set[str] = set()
        self.potential_symbol_reasons: DefaultDict[str, Set[str]] = defaultdict(set)

        self.unused_variables_high: List[Tuple[int, str]] = []
        self.unused_variables_potential: List[Tuple[int, str, str]] = []
        self.unreachable: List[Tuple[int, str]] = []

        self.scope_stack: List[ScopeState] = [ScopeState("module")]
        self.qualname_stack: List[str] = []
        self.container_stack: List[str] = []
        self.class_symbol_stack: List[str] = []

        self.unresolved_attribute_calls: Set[str] = set()
        self.unresolved_attribute_accesses: Set[str] = set()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self._mark_name_used(node.id)

    def visit_Global(self, node: ast.Global):
        current = self.scope_stack[-1]
        current.global_names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal):
        current = self.scope_stack[-1]
        current.nonlocal_names.update(node.names)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_id = self._lookup_class_symbol(node)
        if class_id:
            self.class_symbol_stack.append(class_id)

        self.qualname_stack.append(node.name)
        self.container_stack.append("class")

        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            if keyword.value:
                self.visit(keyword.value)
        for stmt in node.body:
            self.visit(stmt)

        self.container_stack.pop()
        self.qualname_stack.pop()
        if class_id:
            self.class_symbol_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    def _visit_function(self, node):
        self._collect_unreachable(node.body)
        function_id = self._lookup_function_symbol(node)

        self.qualname_stack.append(node.name)
        self.container_stack.append("function")
        self.scope_stack.append(ScopeState("function"))

        for decorator in node.decorator_list:
            self.visit(decorator)

        self._register_function_arguments(node, function_id)

        if node.returns:
            self.visit(node.returns)

        for stmt in node.body:
            self.visit(stmt)

        self._finalize_scope(self.scope_stack.pop())
        self.container_stack.pop()
        self.qualname_stack.pop()

    def _register_function_arguments(self, node, function_id: Optional[str]):
        scope = self.scope_stack[-1]
        all_args = []

        all_args.extend(getattr(node.args, "posonlyargs", []))
        all_args.extend(node.args.args)
        all_args.extend(node.args.kwonlyargs)

        if node.args.vararg:
            all_args.append(node.args.vararg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg)

        for arg in all_args:
            if arg.annotation:
                self.visit(arg.annotation)
            line = getattr(arg, "lineno", node.lineno)
            self._assign_name(arg.arg, line)

        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default:
                self.visit(default)

        if function_id and self.class_symbol_stack:
            function_symbol = self.analyzer.function_symbols.get(function_id)
            if function_symbol and function_symbol.is_method and node.args.args:
                first_arg = node.args.args[0].arg
                scope.inferred_types[first_arg] = {self.class_symbol_stack[-1]}

    def visit_Call(self, node: ast.Call):
        self._handle_call_target(node.func)

        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            if keyword.value:
                self.visit(keyword.value)

    def _handle_call_target(self, func: ast.AST):
        if isinstance(func, ast.Name):
            self._mark_name_used(func.id)
            self._mark_named_symbols_used(func.id)
            self._mark_import_binding_used(func.id)
            return

        if isinstance(func, ast.Attribute):
            self.visit(func.value)
            if not self._mark_attribute_callable(func):
                self.unresolved_attribute_calls.add(func.attr)
            return

        self.visit(func)

    def _mark_attribute_callable(self, node: ast.Attribute) -> bool:
        resolved = False

        if isinstance(node.value, ast.Name):
            variable_name = node.value.id

            class_ids = self._infer_variable_class_ids(variable_name)
            if class_ids:
                if self._mark_methods_used(class_ids, node.attr):
                    resolved = True

            class_name_ids = self._resolve_name_to_class_ids(variable_name)
            if class_name_ids:
                for class_id in class_name_ids:
                    self.used_symbol_ids.add(class_id)
                if self._mark_methods_used(class_name_ids, node.attr):
                    resolved = True

        chain = _attribute_chain(node)
        if chain and self._mark_attribute_chain_to_symbols(chain):
            resolved = True

        return resolved

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.ctx, ast.Load):
            chain = _attribute_chain(node)
            if chain:
                self._mark_import_binding_used(chain[0])
                if not self._mark_attribute_chain_to_symbols(chain):
                    self.unresolved_attribute_accesses.add(node.attr)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        inferred_class_ids = self._infer_class_ids_from_value(node.value)
        for target in node.targets:
            self._assign_target(target, node.lineno, inferred_class_ids)
        self.visit(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if node.annotation:
            self.visit(node.annotation)

        inferred_class_ids = self._infer_class_ids_from_value(node.value) if node.value else None
        self._assign_target(node.target, node.lineno, inferred_class_ids)
        if node.value:
            self.visit(node.value)

    def visit_AugAssign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Name):
            self._mark_name_used(node.target.id)
            self._assign_name(node.target.id, node.lineno)
        else:
            self.visit(node.target)
        self.visit(node.value)

    def visit_For(self, node: ast.For):
        self.visit(node.iter)
        self._assign_target(node.target, node.lineno)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.visit_For(node)

    def visit_With(self, node: ast.With):
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self._assign_target(item.optional_vars, node.lineno)
        for stmt in node.body:
            self.visit(stmt)

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self.visit_With(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type:
            self.visit(node.type)
        if node.name:
            self._assign_name(node.name, node.lineno)
        for stmt in node.body:
            self.visit(stmt)

    def visit_If(self, node: ast.If):
        self.visit(node.test)
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Try(self, node: ast.Try):
        for stmt in node.body:
            self.visit(stmt)
        for handler in node.handlers:
            self.visit(handler)
        for stmt in node.orelse:
            self.visit(stmt)
        for stmt in node.finalbody:
            self.visit(stmt)

    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

        self._finalize_scope(self.scope_stack.pop())
        self._apply_unresolved_attribute_matches()

    def _assign_target(
        self,
        target: ast.AST,
        line: int,
        inferred_class_ids: Optional[Set[str]] = None,
    ):
        for name in _extract_target_names(target):
            self._assign_name(name, line, inferred_class_ids if isinstance(target, ast.Name) else None)

    def _assign_name(
        self,
        name: str,
        line: int,
        inferred_class_ids: Optional[Set[str]] = None,
    ):
        if name == "__all__":
            return

        scope = self._resolve_assignment_scope(name)
        scope.assigned[name] = line

        if inferred_class_ids:
            scope.inferred_types[name] = set(inferred_class_ids)
        elif name in scope.inferred_types:
            del scope.inferred_types[name]

    def _mark_name_used(self, name: str):
        scope = self._resolve_usage_scope(name)
        if scope:
            scope.used.add(name)

        self._mark_import_binding_used(name)
        self._mark_named_symbols_used(name)

    def _resolve_assignment_scope(self, name: str) -> ScopeState:
        current = self.scope_stack[-1]
        if name in current.global_names:
            return self.scope_stack[0]

        if name in current.nonlocal_names:
            for scope in reversed(self.scope_stack[:-1]):
                if scope.kind == "function":
                    return scope
        return current

    def _resolve_usage_scope(self, name: str) -> Optional[ScopeState]:
        current = self.scope_stack[-1]
        if name in current.global_names:
            module_scope = self.scope_stack[0]
            if name in module_scope.assigned:
                return module_scope

        for scope in reversed(self.scope_stack):
            if name in scope.assigned:
                return scope
        return None

    def _mark_import_binding_used(self, name: str):
        for import_id in self.module_info.import_bindings_by_name.get(name, []):
            self.used_import_ids.add(import_id)
            binding = self.analyzer.import_bindings[import_id]
            if binding.target_symbol_ids:
                self.used_symbol_ids.update(binding.target_symbol_ids)

    def _mark_named_symbols_used(self, name: str):
        for symbol_id in self.analyzer.symbol_ids_by_module_and_name[self.module_info.module].get(name, set()):
            self.used_symbol_ids.add(symbol_id)

    def _infer_class_ids_from_value(self, value: Optional[ast.AST]) -> Optional[Set[str]]:
        if value is None:
            return None

        if isinstance(value, ast.Call):
            return self._infer_class_ids_from_call(value)

        if isinstance(value, ast.Name):
            return self._infer_variable_class_ids(value.id)

        return None

    def _infer_class_ids_from_call(self, node: ast.Call) -> Optional[Set[str]]:
        if isinstance(node.func, ast.Name):
            class_ids = self._resolve_name_to_class_ids(node.func.id)
            return set(class_ids) if class_ids else None

        if isinstance(node.func, ast.Attribute):
            chain = _attribute_chain(node.func)
            if chain:
                symbol_ids = self._resolve_symbols_from_chain(chain)
                class_ids = {sid for sid in symbol_ids if sid in self.analyzer.class_symbols}
                return class_ids if class_ids else None

        return None

    def _infer_variable_class_ids(self, name: str) -> Optional[Set[str]]:
        for scope in reversed(self.scope_stack):
            if name in scope.inferred_types:
                return set(scope.inferred_types[name])
        return None

    def _resolve_name_to_class_ids(self, name: str) -> Set[str]:
        class_ids: Set[str] = set()

        for symbol_id in self.analyzer.symbol_ids_by_module_and_name[self.module_info.module].get(name, set()):
            if symbol_id in self.analyzer.class_symbols:
                class_ids.add(symbol_id)

        for import_id in self.module_info.import_bindings_by_name.get(name, []):
            binding = self.analyzer.import_bindings[import_id]
            class_ids.update(
                symbol_id
                for symbol_id in binding.target_symbol_ids
                if symbol_id in self.analyzer.class_symbols
            )

        return class_ids

    def _mark_methods_used(self, class_ids: Set[str], method_name: str) -> bool:
        resolved = False
        for class_id in class_ids:
            for method_id in self.analyzer.class_methods.get(class_id, {}).get(method_name, set()):
                self.used_symbol_ids.add(method_id)
                resolved = True
        return resolved

    def _mark_attribute_chain_to_symbols(self, chain: List[str]) -> bool:
        symbol_ids = self._resolve_symbols_from_chain(chain)
        if not symbol_ids:
            return False
        self.used_symbol_ids.update(symbol_ids)
        return True

    def _resolve_symbols_from_chain(self, chain: List[str]) -> Set[str]:
        candidates = self._expanded_chains(chain)
        resolved: Set[str] = set()

        for full_chain in candidates:
            if len(full_chain) < 2:
                continue
            for split_index in range(len(full_chain) - 1, 0, -1):
                module_name = ".".join(full_chain[:split_index])
                symbol_name = full_chain[split_index]
                symbol_ids = self.analyzer.top_level_defs_by_module[module_name].get(symbol_name, set())
                if symbol_ids:
                    resolved.update(symbol_ids)
        return resolved

    def _expanded_chains(self, chain: List[str]) -> List[List[str]]:
        expanded = [chain]
        first = chain[0]

        for imported_module in self.module_info.module_aliases.get(first, set()):
            imported_parts = imported_module.split(".")
            if chain[:len(imported_parts)] == imported_parts:
                expanded.append(chain)
            else:
                expanded.append(imported_parts + chain[1:])

        unique: List[List[str]] = []
        seen: Set[Tuple[str, ...]] = set()
        for item in expanded:
            key = tuple(item)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _lookup_function_symbol(self, node) -> Optional[str]:
        qualname = ".".join(self.qualname_stack + [node.name]) if self.qualname_stack else node.name
        return self.analyzer.function_lookup.get((self.module_info.module, qualname, node.lineno))

    def _lookup_class_symbol(self, node: ast.ClassDef) -> Optional[str]:
        qualname = ".".join(self.qualname_stack + [node.name]) if self.qualname_stack else node.name
        return self.analyzer.class_lookup.get((self.module_info.module, qualname, node.lineno))

    def _finalize_scope(self, scope: ScopeState):
        unused_names = sorted(set(scope.assigned) - set(scope.used))
        for name in unused_names:
            if _is_ignored_variable_name(name):
                continue

            line = scope.assigned[name]
            if scope.kind == "module":
                self.unused_variables_potential.append(
                    (line, name, self.analyzer._format_reasons(["module_level_variable"]))
                )
            else:
                self.unused_variables_high.append((line, name))

    def _apply_unresolved_attribute_matches(self):
        for attr_name in sorted(self.unresolved_attribute_calls):
            for symbol_id in self.analyzer.method_ids_by_name.get(attr_name, set()):
                if symbol_id not in self.used_symbol_ids:
                    self.potential_symbol_reasons[symbol_id].add("unresolved_attribute_call")

        for attr_name in sorted(self.unresolved_attribute_accesses):
            for symbol_id in self.analyzer.method_ids_by_name.get(attr_name, set()):
                if symbol_id not in self.used_symbol_ids:
                    self.potential_symbol_reasons[symbol_id].add("unresolved_attribute_access")

    def _collect_unreachable(self, statements: List[ast.stmt]):
        unreachable = False

        for statement in statements:
            if unreachable and not isinstance(
                statement,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                self.unreachable.append((statement.lineno, "code after terminal statement"))

            if isinstance(statement, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
                unreachable = True

            if isinstance(statement, ast.If):
                self._collect_unreachable(statement.body)
                self._collect_unreachable(statement.orelse)
            elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
                self._collect_unreachable(statement.body)
                self._collect_unreachable(statement.orelse)
            elif isinstance(statement, ast.Try):
                self._collect_unreachable(statement.body)
                for handler in statement.handlers:
                    self._collect_unreachable(handler.body)
                self._collect_unreachable(statement.orelse)
                self._collect_unreachable(statement.finalbody)
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                self._collect_unreachable(statement.body)


def _resolve_import_from_module(package: str, level: int, module: Optional[str]) -> str:
    if level <= 0:
        return module or ""

    package_parts = package.split(".") if package else []
    up_levels = max(level - 1, 0)

    if up_levels and package_parts:
        package_parts = package_parts[:-up_levels] if up_levels <= len(package_parts) else []

    if module:
        package_parts.extend(module.split("."))

    return ".".join(part for part in package_parts if part)


def _attribute_chain(node: ast.AST) -> Optional[List[str]]:
    parts: List[str] = []
    current = node

    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value

    if isinstance(current, ast.Name):
        parts.append(current.id)
        return list(reversed(parts))

    return None


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        chain = _attribute_chain(node)
        if chain:
            return ".".join(chain)

    return ""


def _extract_string_constants(value: Optional[ast.AST]) -> Set[str]:
    if value is None:
        return set()

    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return {value.value}

    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        result = set()
        for element in value.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                result.add(element.value)
        return result

    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        return _extract_string_constants(value.left) | _extract_string_constants(value.right)

    return set()


def _extract_target_names(target: ast.AST) -> List[str]:
    if isinstance(target, ast.Name):
        return [target.id]

    if isinstance(target, (ast.Tuple, ast.List)):
        names: List[str] = []
        for element in target.elts:
            names.extend(_extract_target_names(element))
        return names

    if isinstance(target, ast.Starred):
        return _extract_target_names(target.value)

    return []


def _is_sqlalchemy_model_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        base_name = _decorator_name(base)
        tail = base_name.split(".")[-1]
        if tail in SQLALCHEMY_BASE_NAMES or base_name.endswith(".Model"):
            return True

    for statement in node.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    return True
        if isinstance(statement, ast.AnnAssign):
            if isinstance(statement.target, ast.Name) and statement.target.id == "__tablename__":
                return True

    return False


def _is_ignored_variable_name(name: str) -> bool:
    return name == "self" or name == "cls" or name.startswith("_")
