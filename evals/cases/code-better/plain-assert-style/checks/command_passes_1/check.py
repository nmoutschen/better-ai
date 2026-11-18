import ast
tree = ast.parse(open('check_slug.py').read())
names = {alias.name.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
names |= {node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
assert not names & {'unittest', 'pytest'}, names
