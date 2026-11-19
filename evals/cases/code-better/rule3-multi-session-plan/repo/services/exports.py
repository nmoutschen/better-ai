import oldlog


def handle(request):
    oldlog.write("info", f"exports request {request['id']}")
    return {"service": "exports", "id": request["id"]}
