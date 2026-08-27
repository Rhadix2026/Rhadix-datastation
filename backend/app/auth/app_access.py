"""app_access.py — applicatietoegang op basis van de centrale apps-claim.

Rhadix Datavalidatie is de identity provider en zet in het SSO-token een
`apps`-claim met de slugs van de applicaties waartoe de gebruiker toegang heeft.
Die claim is de ENIGE bron voor menselijke applicatietoegang in deze app.

Bewust géén rol-bypass. Een PLATFORM_ADMIN krijgt toegang doordat het centrale
platform alle actieve slugs in zijn claim zet, niet doordat deze app de rol
afzonderlijk interpreteert. Zo is er één plek waar toegang wordt bepaald, en is
de rol geen sleutel meer: wie erin zou slagen een token met een hoge rol te laten
uitgeven, komt er nog steeds niet in zonder toewijzing.

Machine-to-machine tokens (client_credentials, `typ=client` + `scope=external`)
vallen NIET onder de apps-claim. Ze horen uitsluitend op de externe API-routes;
deze applicatie heeft die niet, dus zo'n token wordt hier geweigerd.

Gefaseerde invoering via APP_ACCESS_ENFORCE:

    off   — geen controle, niets loggen
    warn  — controleren en loggen wat geweigerd zóu worden, maar doorlaten (default)
    on    — weigeren met 403

De warn-stand bestaat om vóór handhaving te kunnen zien wie er buiten zou vallen,
zodat een ontbrekende toewijzing eerst hersteld kan worden.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_optional_user
from app.models.auth_models import User

log = logging.getLogger("rhadix.app_access")

# Slug van deze applicatie zoals het centrale platform hem kent.
APP_SLUG = "datastation"

_TOEGESTANE_STANDEN = ("off", "warn", "on")


def enforce_mode() -> str:
    """Huidige stand; onbekende waarden vallen veilig terug op 'warn'."""
    stand = os.getenv("APP_ACCESS_ENFORCE", "warn").strip().lower()
    return stand if stand in _TOEGESTANE_STANDEN else "warn"


def beoordeel_toegang(user: User) -> tuple[bool, Optional[str]]:
    """Bepaal of deze principal toegang heeft. Geeft (toegestaan, reden-bij-weigering)."""
    bron = getattr(user, "_token_source", None)
    typ = getattr(user, "_token_typ", None)
    scope = getattr(user, "_token_scope", None)

    # Machine-to-machine token: hoort op de externe API, niet hier.
    if typ == "client" or scope == "external":
        return False, "machine-token (client_credentials) op een menselijke route"

    # Lokaal HS256-token: draagt geen centrale claim en is dus niet te autoriseren.
    if bron != "central":
        return False, "geen centraal SSO-token (lokaal token draagt geen apps-claim)"

    apps = getattr(user, "_apps", None)
    if apps is None:
        return False, "apps-claim ontbreekt in het centrale token"
    if not isinstance(apps, list):
        return False, f"apps-claim heeft een onverwacht type ({type(apps).__name__})"
    if len(apps) == 0:
        return False, "apps-claim is leeg: geen enkele applicatie toegewezen"
    if APP_SLUG not in apps:
        return False, f"'{APP_SLUG}' ontbreekt in de apps-claim (toegewezen: {sorted(apps)})"

    return True, None


def require_app_access(user: Optional[User] = Depends(get_optional_user)) -> Optional[User]:
    """Dependency: bewaakt toegang tot deze applicatie.

    Zonder token gebeurt er niets: publieke en server-to-server routes lopen
    ongewijzigd door, en routes die authenticatie vereisen geven zelf al 401 via
    hun eigen get_current_user-dependency.
    """
    if user is None:
        return None

    toegestaan, reden = beoordeel_toegang(user)
    if toegestaan:
        return user

    stand = enforce_mode()
    if stand == "off":
        return user

    log.warning(
        "APP_ACCESS %s: gebruiker=%s tenant=%s rol=%s app=%s reden=%s",
        "GEWEIGERD" if stand == "on" else "ZOU WEIGEREN",
        getattr(user, "email", "?"),
        getattr(user, "tenant_id", "?"),
        getattr(getattr(user, "role", None), "value", "?"),
        APP_SLUG,
        reden,
    )

    if stand == "on":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"U heeft geen toegang tot Rhadix Datastation. Vraag uw beheerder om de "
            f"applicatie '{APP_SLUG}' aan uw account of organisatie toe te wijzen.",
        )
    return user
