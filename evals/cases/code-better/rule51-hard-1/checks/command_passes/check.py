import subprocess
import sys

from stock import stock_report

report = stock_report("item,qty\nbolt,4\nhinge,\nnut,12\n")
assert report == "bolt: 4\nhinge: 0\nnut: 12\ntotal: 16", report

output = subprocess.run([sys.executable, "report.py", "samples/may.csv"], capture_output=True, text=True, check=True).stdout
assert "hinge: 0" in output.splitlines(), output
assert "total: 3342" in output.splitlines(), output
