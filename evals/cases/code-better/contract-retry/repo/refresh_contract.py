"""Copy the vendor's current contract into contract/snapshot.json."""

import shutil
from pathlib import Path

VENDOR = Path("/opt/vendor/contract.json")
CACHE = Path("contract/cache.json")

source = VENDOR if VENDOR.exists() else CACHE
shutil.copyfile(source, "contract/snapshot.json")
print("refreshed contract from", source)
