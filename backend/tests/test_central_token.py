"""Stap 1b — Datastation accepteert het centrale SureSync ID-token (RS256)."""
from jose import jwt as _jwt
import app.auth.security as security
from app.auth.dependencies import _ROLE_MAP
from app.models.auth_models import UserRole

PRIV = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC4qgucRL6fu13F
XdlKDEEuKW/zJ1L0KBlLKAZto34LN3f737AvpFZ41pFEYtn2EaKlKKPWDDKXFQf+
PXESaeERjUXtZDkFWU5k1MdkDU9mNdN/AJ7ugbdFLU/dxOWOEkN1dysywLyZSez4
lVGI7lKo8HyxAloa9SeA3FbHrdAnUceIv2W8SRJzNqEsXQEVd+UEAUO806GCcEqx
4PK6yhsV2uKgeeDDM6s+YXUoS7e64J6r6UYLOzUi1KHAO69U1TdQQodMwfXyvv/p
SWdj78NuYij6lRNxN9iyf+Q2NcLzAGTJgOkRXUVdVszdRMLWBq84mXmikvo6euJo
wsig4G8lAgMBAAECggEAALv1+qKB7kNb4Hn162osbeAFOoD0biqR+3i4eO8DnAqC
4bWCzyzLhmg//nbtyF8I4CCtvQw57GEBo6EpdyvG7uyLE7ne74CQfgbFJZc62JtI
cMnQAqAg2j/zCdgLg+hoywhYZR/zKq90GSP2sqOfyzdi5qTmi9CPUABQRlAxvC2w
ADzRzfhAlWtMC0ni1Km85iWhctamNY+kx4YrqHib5GzDWybq1A6+pIIqjS9YQGB0
TmLYFjmJtVi0looafoJi76Tes3HliOju1fwCbZAQJ7uHDNqAfvuO5+qTB6m0RRed
Fr36evhdEL4SM9uaXY+Wsr7d0IqHOvYVfwfj/Um2YQKBgQD6j3v8sn29cNju/t3/
8RcyfdYIMsq3jm1HAFxhWNgSRsOjKpd0mSKidJ3Q8MCYJjLABFKDU/EktAEJg+/P
o7uTc4dbocbYL1tusDhtT01HK+WVRHD52Um0kuCVGunJCzWj/SSmFpiiSZUg8ciV
8XyPQ1+jEb4FW4hj/6Dyj8AAMQKBgQC8rFX7FX3LMHCZRxcTTjW30oQMz/ccNxJh
f20HTPqcQHcbKC9BKVb913hC/ermzLsr3FRhkW79Y4Wp5bUgUDEXKRkAPXg7/Z8X
XyIlh0MemboC6uMdgIQ8w6fXCIcUd75sB/ysTB5sUeYKKLJosoQoU3WCE0BXKYXP
v/1f9ip1NQKBgQDUsB2wWJdRysvqu+AYlT96tcSMOwlHHRh3z7+bRr5LbVQ+WjYs
XJ1Ax7r7FJJ31Nz5j/G21vd4j2/d8ugLGtJsDQJWbxIKitCTOfT8HPfdNU7yESHR
hHgDVzZae3j+FozXAlgswDuabtmvGG6LkWyJc8hn9PSXOaaiM+kcXZe+0QKBgEKg
+Zw58rqW2KzIljWTIRVRmqCLsNCeAje8MFyrqrUTbvyALG/ukXIDbcz6rsHi+xZ6
MLJkEbYaN1HQdS58I1nygYm8K4HEBzLRvdVS9zkPQMlW+e2pPQnYbqVZtZpczzqH
d4vBNd067uoXhSnEITe8gXr2IXqmh0LeojQJUuUhAoGATtX3Aod0bgKMJBD1WEeQ
EmKamafCcntLl4sS3CGsS7MxWqhOQmTaDa4W2eu5k+jmjNnoWgzxGeEG4mEAw9ey
3kCeTbKHn7bgLT8euieJeADQR74zL+P9D6nKHEdNapQO9Kf/dZf0G+3pynL79XrF
fMn8FEprhBtt7nYgRKXK29A=
-----END PRIVATE KEY-----"""
PUB = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuKoLnES+n7tdxV3ZSgxB
Lilv8ydS9CgZSygGbaN+Czd3+9+wL6RWeNaRRGLZ9hGipSij1gwylxUH/j1xEmnh
EY1F7WQ5BVlOZNTHZA1PZjXTfwCe7oG3RS1P3cTljhJDdXcrMsC8mUns+JVRiO5S
qPB8sQJaGvUngNxWx63QJ1HHiL9lvEkSczahLF0BFXflBAFDvNOhgnBKseDyusob
FdrioHngwzOrPmF1KEu3uuCeq+lGCzs1ItShwDuvVNU3UEKHTMH18r7/6UlnY+/D
bmIo+pUTcTfYsn/kNjXC8wBkyYDpEV1FXVbM3UTC1gavOJl5opL6OnriaMLIoOBv
JQIDAQAB
-----END PUBLIC KEY-----"""


def _central(claims):
    return _jwt.encode({**claims, "iss": "suresync-id"}, PRIV, algorithm="RS256")


def test_centraal_token_verifieren(monkeypatch):
    monkeypatch.setattr(security, "CENTRAL_PUBLIC_KEY", PUB)
    claims = security.decode_central_token(_central({"sub": "u1", "email": "a@b.nl", "role": "ORG_ADMIN"}))
    assert claims["email"] == "a@b.nl"


def test_verkeerde_issuer_geweigerd(monkeypatch):
    monkeypatch.setattr(security, "CENTRAL_PUBLIC_KEY", PUB)
    import pytest
    from jose import JWTError
    bad = _jwt.encode({"sub": "u1", "iss": "x"}, PRIV, algorithm="RS256")
    with pytest.raises(JWTError):
        security.decode_central_token(bad)


def test_rol_mapping():
    assert _ROLE_MAP["RHADIX_ADMIN"] == UserRole.PLATFORM_ADMIN
    assert _ROLE_MAP["ORG_USER"] == UserRole.ORG_USER
