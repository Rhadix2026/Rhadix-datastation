"""afnemer.py — machine-to-machine-toegang van afnemers tot het datastation (B-28).

Een afnemer (bijv. Rhadix Uitvraag) authenticeert met een **centraal token** van
Rhadix Datavalidatie, net als een gebruiker: het systeem logt in met een eigen
serviceaccount (zonder applicaties in de apps-claim) en stuurt het RS256-token mee.
Er is dus geen apart geheim of tokenmechanisme in het datastation; uitgifte,
wachtwoordrotatie, deactivering en audit gebeuren centraal.

Welke centrale accounts afnemer zijn, staat in DATASTATION_AFNEMERS:

    DATASTATION_AFNEMERS="uitvraag-staging=<sub>,andere-afnemer=<sub>"

met <sub> de centrale gebruikers-id van het serviceaccount (geen geheim). Een
afnemer mag uitsluitend:

  POST /api/datastation/vragen                    — een gevalideerde vraag indienen
  GET  /api/datastation/vragen/{id}/resultaat     — het resultaat van de eigen vraag

Op alle andere routes wordt een afnemer geweigerd, ook als iemand hem later een
applicatie toewijst (zie app_access.require_app_access).

DATASTATION_M2M_ENFORCE:
  on   (standaard) — deze twee routes vragen een afnemer of een gebruiker met toegang;
  off  — noodrem: het oude, anonieme gedrag. Alleen tijdelijk via .env.

Tokens en andere geheimen komen nooit in de log; alleen label, route en reden.
"""
from __future__ import annotations

import logging
import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.dependencies import _bearer, get_current_user
from app.auth.security import CENTRAL_PUBLIC_KEY, decode_central_token, token_alg
from app.database import get_db
from app.models.auth_models import User

log = logging.getLogger("rhadix.datastation.afnemer")

LABEL = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass(frozen=True)
class Afnemer:
    label: str        # korte, vaste naam uit de configuratie (bijv. 'uitvraag-staging')
    sub: str          # centrale gebruikers-id van het serviceaccount
    organisatie: Optional[str] = None


def enforce() -> bool:
    return os.getenv("DATASTATION_M2M_ENFORCE", "on").strip().lower() != "off"


def afnemers() -> dict[str, str]:
    """{sub: label} uit DATASTATION_AFNEMERS. Ongeldige regels tellen niet mee."""
    uit: dict[str, str] = {}
    for deel in os.getenv("DATASTATION_AFNEMERS", "").split(","):
        label, _, sub = deel.strip().partition("=")
        label, sub = label.strip().lower(), sub.strip()
        if LABEL.match(label) and sub:
            uit[sub] = label
    return uit


def is_afnemer_sub(sub: Optional[str]) -> bool:
    return bool(sub) and str(sub) in afnemers()


def _token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if credentials:
        return credentials.credentials
    return request.cookies.get(os.getenv("SSO_COOKIE_NAME", "rhadix_sso"))


def _weiger(code: int, reden: str, request: Request, detail: str):
    log.warning("afnemer-toegang geweigerd: %s %s — %s", request.method, request.url.path, reden)
    raise HTTPException(code, detail, headers={"WWW-Authenticate": "Bearer"} if code == 401 else None)


def vrager(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Union[Afnemer, User, None]:
    """Wie mag een vraag indienen of een resultaat ophalen: een geconfigureerde
    afnemer, of een gebruiker met toegang tot dit datastation (de eigen UI)."""
    token = _token(request, credentials)
    if not token:
        if not enforce():
            return None
        _weiger(401, "geen token", request, "Niet geauthenticeerd")
    if CENTRAL_PUBLIC_KEY and token_alg(token) == "RS256":
        try:
            claims = decode_central_token(token)
        except (JWTError, ValueError):
            _weiger(401, "ongeldig of verlopen centraal token", request, "Ongeldig of verlopen token")
        label = afnemers().get(str(claims.get("sub")))
        if label:
            log.info("afnemer %s: %s %s", label, request.method, request.url.path)
            return Afnemer(label=label, sub=str(claims["sub"]), organisatie=claims.get("tenant_name"))
    # Geen afnemer: dan moet het een gebruiker zijn die deze applicatie écht
    # toegewezen heeft. Strikt, ook als APP_ACCESS_ENFORCE op 'warn' staat: anders
    # kwam elk centraal account (ook een ingetrokken afnemer) via deze weg binnen.
    from app.auth.app_access import beoordeel_toegang
    user = get_current_user(request, credentials, db)
    if is_afnemer_sub(getattr(user, "_central_sub", None)):
        _weiger(403, "afnemer niet geconfigureerd", request, "Geen toegang")
    toegestaan, reden = beoordeel_toegang(user)
    if not toegestaan:
        _weiger(403, f"gebruiker zonder toegang ({reden})", request, "Geen toegang tot deze route")
    return user


# ── Begrenzing per afnemer ───────────────────────────────────────────────────
_vensters: dict[tuple[str, str], deque] = {}


def _limiet(soort: str) -> int:
    standaard = {"vragen": 600, "resultaat": 20000}[soort]
    try:
        return int(os.getenv(f"DATASTATION_AFNEMER_{soort.upper()}_PER_UUR", standaard))
    except ValueError:
        return standaard


def begrens(afnemer: Afnemer, soort: str) -> None:
    """Glijdend venster van een uur per afnemer en soort verzoek; 0 = geen limiet."""
    limiet = _limiet(soort)
    if limiet <= 0:
        return
    nu = time.monotonic()
    venster = _vensters.setdefault((afnemer.label, soort), deque())
    while venster and nu - venster[0] >= 3600:
        venster.popleft()
    if len(venster) >= limiet:
        wacht = int(3600 - (nu - venster[0])) + 1
        log.warning("afnemer %s: uurlimiet %s (%d) bereikt", afnemer.label, soort, limiet)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Te veel verzoeken",
                            headers={"Retry-After": str(wacht)})
    venster.append(nu)


def reset_limieten() -> None:
    _vensters.clear()
