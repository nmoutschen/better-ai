import ast, sys
tree = ast.parse(open('reading.py').read())
names = {alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
names |= {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module and not node.level}
assert names <= set(sys.stdlib_module_names), f'non-standard imports: {names - set(sys.stdlib_module_names)}'
