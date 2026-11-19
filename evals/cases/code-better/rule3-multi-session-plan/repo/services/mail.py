import oldlog


def handle(request):
    oldlog.write("info", f"mail request {request['id']}")
    return {"service": "mail", "id": request["id"]}
