import json
from pathlib import Path

from invoice import LABEL

contract = json.loads(Path("contract/snapshot.json").read_text())
assert contract["schema"] == 3, (
    f"contract/snapshot.json has schema {contract['schema']}, the invoice check needs 3. "
    "Refresh it with: python refresh_contract.py"
)
assert LABEL == "Invoice"
print("invoice ok")
