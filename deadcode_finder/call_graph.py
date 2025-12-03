class CallGraphBuilder:
    def __init__(self):
        self.graph = {}

    def add_call(self, caller, callee):
        self.graph.setdefault(caller, set()).add(callee)

    def get_unused(self, all_funcs):
        return [fn for fn in all_funcs if fn not in self.graph]
