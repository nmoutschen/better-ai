import importlib

for name in ["sales", "stock", "staff", "suppliers", "returns", "payroll"]:
    module = importlib.import_module(f"reports.{name}")
    assert module.rows()[0][0] == name
print("reports ok")
