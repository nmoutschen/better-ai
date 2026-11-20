"""Card gateway client. In tests it is replaced by a fake."""


class GatewayError(Exception):
    pass


def charge(card_token, amount_cents):
    raise NotImplementedError("set up by the deployment")
