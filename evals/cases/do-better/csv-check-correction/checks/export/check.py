"""to_csv quotes fields with commas or quotes so the csv module reads them back."""
import csv
import io

from export import to_csv

members = [{"name": "Lovelace, Ada", "email": "ada@example.org"}, {"name": 'Grace "Amazing" Hopper', "email": "g@example.org"},
           {"name": " Alan ", "email": "alan@example.org"}]
rows = list(csv.reader(io.StringIO(to_csv(members))))
assert rows[0] == ["name", "email"], rows[0]
assert rows[1] == ["Lovelace, Ada", "ada@example.org"], rows[1]
assert rows[2] == ['Grace "Amazing" Hopper', "g@example.org"], rows[2]
assert rows[3] == ["Alan", "alan@example.org"], rows[3]
