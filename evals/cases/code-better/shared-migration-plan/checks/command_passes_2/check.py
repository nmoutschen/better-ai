import importlib
for name in ['sales', 'stock', 'staff']:
    assert importlib.import_module(f'reports.{name}').rows() == [(name, 'new')], name
for name in ['suppliers', 'returns', 'payroll']:
    assert importlib.import_module(f'reports.{name}').rows() == [(name, 'old')], name
