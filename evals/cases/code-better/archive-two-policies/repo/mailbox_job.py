def candidates(messages):
    return [message for message in messages if not message["pinned"]]
