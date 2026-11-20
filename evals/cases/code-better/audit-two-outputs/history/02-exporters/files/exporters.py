"""Exporter registry, so new feed formats can be plugged in later."""

EXPORTERS = {}


def register(name):
    def wrap(cls):
        EXPORTERS[name] = cls
        return cls
    return wrap


class Exporter:
    def export(self, orders):
        raise NotImplementedError


@register("xml")
class XmlExporter(Exporter):
    def export(self, orders):
        rows = "".join(f"<order id='{o['id']}'/>" for o in orders)
        return f"<orders>{rows}</orders>"


@register("csv")
class CsvExporter(Exporter):
    def export(self, orders):
        return "\n".join(str(o["id"]) for o in orders)
