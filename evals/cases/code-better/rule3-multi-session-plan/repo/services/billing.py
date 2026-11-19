import oldlog


def handle(request):
    oldlog.write("info", f"billing request {request['id']}")
    return {"service": "billing", "id": request["id"]}
