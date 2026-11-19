from weather import forecast


def widgets():
    """Each widget is one line of text, keyed by widget name."""
    return {"weather": forecast()}
