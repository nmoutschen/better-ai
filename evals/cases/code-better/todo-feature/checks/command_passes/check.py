import ast, inspect
from cart import total
assert list(inspect.signature(total).parameters) == ['lines']
assert total([(2.0, 3), (1.5, 2)]) == 9.0
assert total([]) == 0
names = {getattr(n, 'name', None) or getattr(getattr(n, 'targets', [None])[0], 'id', None) for n in ast.parse(open('cart.py').read()).body}
assert names <= {'total', None}, f'new top-level code: {names}'
