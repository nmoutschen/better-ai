import oldlog


def handle(request):
    oldlog.write("info", f"search request {request['id']}")
    return {"service": "search", "id": request["id"]}
