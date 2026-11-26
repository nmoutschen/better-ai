"""WebAuthn registration (none attestation) and authentication for one localhost ES256 credential."""

import base64
import hashlib
import json
import re

P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
G = (
    0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
    0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
)
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
RP_HASH = hashlib.sha256(b"localhost").digest()


def require(condition):
    if not condition:
        raise ValueError("Invalid WebAuthn proof")


def decode(value):
    require(isinstance(value, str) and len(value) <= 65536 and re.fullmatch(r"[A-Za-z0-9_-]+", value))
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)


class Reader:
    """Read only definite-length CBOR data types used by none attestation and ES256 COSE keys."""

    def __init__(self, data):
        self.data = data
        self.pos = 0

    def take(self, size):
        require(size <= len(self.data) - self.pos)
        result = self.data[self.pos : self.pos + size]
        self.pos += size
        return result

    def cbor(self, depth=0):
        require(depth < 8)
        kind, length = divmod(self.take(1)[0], 32)
        if length >= 24:
            require(length <= 26)
            length = int.from_bytes(self.take(1 << (length - 24)), "big")
        if kind == 0:
            return length
        if kind == 1:
            return -1 - length
        if kind == 2:
            return self.take(length)
        if kind == 3:
            return self.take(length).decode("utf-8")
        require(kind == 5 and length <= 64)
        value = {}
        for _ in range(length):
            key = self.cbor(depth + 1)
            require(isinstance(key, (int, str)) and key not in value)
            value[key] = self.cbor(depth + 1)
        return value


def cbor_map(data):
    reader = Reader(data)
    value = reader.cbor()
    require(reader.pos == len(data) and isinstance(value, dict))
    return value


def client(proof, ceremony, challenge, origin):
    require(isinstance(proof, dict) and proof.get("type") == "public-key")
    response = proof.get("response")
    require(isinstance(response, dict))
    raw = decode(response.get("clientDataJSON"))
    fields = json.loads(raw)
    require(
        isinstance(fields, dict)
        and fields.get("type") == "webauthn." + ceremony
        and fields.get("challenge") == challenge
        and fields.get("origin") == origin
        and fields.get("crossOrigin", False) is False
        and "topOrigin" not in fields
    )
    return response, hashlib.sha256(raw).digest()


def auth_flags(data, registration):
    require(len(data) >= 37 and data[:32] == RP_HASH)
    flags = data[32]
    require(flags & 1 and bool(flags & 64) == registration and not flags & 128)
    require(not flags & 16 or flags & 8)


def public_point(xbytes, ybytes):
    require(isinstance(xbytes, bytes) and isinstance(ybytes, bytes) and len(xbytes) == len(ybytes) == 32)
    x, y = int.from_bytes(xbytes, "big"), int.from_bytes(ybytes, "big")
    require(x < P and y < P and (y * y - x * x * x + 3 * x - B) % P == 0)
    return x, y


def register(proof, challenge, origin):
    response, _ = client(proof, "create", challenge, origin)
    raw_id = decode(proof.get("rawId"))
    att = cbor_map(decode(response.get("attestationObject")))
    require(att.get("fmt") == "none" and att.get("attStmt") == {})
    data = att.get("authData")
    require(isinstance(data, bytes) and len(data) >= 55)
    auth_flags(data, True)
    length = int.from_bytes(data[53:55], "big")
    require(0 < length <= 1023 and raw_id == data[55 : 55 + length] and len(raw_id) == length)
    key = cbor_map(data[55 + length :])
    require(key.get(1) == 2 and key.get(3) == -7 and key.get(-1) == 1)
    public_point(key.get(-2), key.get(-3))
    return {"id": proof["rawId"], "x": key[-2].hex(), "y": key[-3].hex()}


def point_sum(a, b):
    if a is None:
        return b
    if b is None:
        return a
    x, y = a
    u, v = b
    if x == u:
        if (y + v) % P == 0:
            return None
        slope = (3 * x * x - 3) * pow(2 * y, -1, P)
    else:
        slope = (v - y) * pow(u - x, -1, P)
    new_x = (slope * slope - x - u) % P
    return new_x, (slope * (x - new_x) - y) % P


def multiply(n, point):
    result = None
    while n:
        if n & 1:
            result = point_sum(result, point)
        point = point_sum(point, point)
        n >>= 1
    return result


def der_integer(reader):
    require(reader.take(1) == b"\x02")
    size = reader.take(1)[0]
    require(1 <= size <= 33)
    raw = reader.take(size)
    require(raw[0] < 128 and (size == 1 or raw[0] or raw[1] >= 128))
    number = int.from_bytes(raw, "big")
    require(0 < number < N)
    return number


def verify(proof, challenge, origin, credential):
    response, client_hash = client(proof, "get", challenge, origin)
    require(proof.get("rawId") == credential["id"])
    data = decode(response.get("authenticatorData"))
    auth_flags(data, False)
    require(len(data) == 37)
    blob = decode(response.get("signature"))
    reader = Reader(blob)
    require(reader.take(1) == b"\x30" and reader.take(1)[0] == len(blob) - 2)
    r, s = der_integer(reader), der_integer(reader)
    require(reader.pos == len(blob))
    public = public_point(bytes.fromhex(credential["x"]), bytes.fromhex(credential["y"]))
    digest = int.from_bytes(hashlib.sha256(data + client_hash).digest(), "big")
    inverse = pow(s, -1, N)
    point = point_sum(multiply(digest * inverse % N, G), multiply(r * inverse % N, public))
    require(point is not None and point[0] % N == r)
