import oldlog


def handle(request):
    oldlog.write("info", f"auth request {request['id']}")
    return {"service": "auth", "id": request["id"]}
