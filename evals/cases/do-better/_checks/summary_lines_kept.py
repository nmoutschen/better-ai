"""The summary lines the late update does not touch (pricing, payments, support, next meeting) are still in summary.md."""
import sys

planted = open(sys.argv[1]).read().splitlines()
current = open("summary.md").read()
kept = ("Pricing:", "Payments:", "Support:", "Next meeting:")
missing = [line for line in planted if line.strip().startswith(tuple("- " + key for key in kept)) and line.strip() not in current]
assert not missing, missing
