import io, json, contextlib
from report import main
out = io.StringIO()
with contextlib.redirect_stdout(out):
    main(['--json'])
assert json.loads(out.getvalue()) == {'count': 3, 'total': 12}
out = io.StringIO()
with contextlib.redirect_stdout(out):
    main([])
assert out.getvalue() == '3 rows, total 12\n'
