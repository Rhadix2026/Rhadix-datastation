"""
test_lokaal_gebruikersbeheer.py — wat lokaal gebruikersbeheer in deze applicatie doet.

Bevinding 13 uit het bevindingenregister ging over de uiteenlopende look & feel van de
beheerschermen. De oorzaak eronder is inhoudelijk: het scherm bood knoppen die niets
opleveren. 'Nieuwe gebruiker' en 'Wachtwoord' zijn daarom uit het scherm gehaald —
aanmaken en wachtwoorden zetten gebeurt in Rhadix Datavalidatie, waar het wél werkt.

De endpoints zijn bewust ongemoeid gelaten; er is uitsluitend een schermwijziging.
Deze suite legt vast waarom die knoppen konden vervallen, en legt daarnaast een
afwijking vast die tijdens de analyse boven kwam en die NIET in deze wijziging is
opgelost (zie TestBekendeAfwijking).
"""
import pytest

from app.auth.router import local_login_enabled
from app.auth.security import hash_password
from app.database import SessionLocal
from app.models.auth_models import Tenant, User, UserRole

from tests._testkeys import central_token

BESCHERMD = "/api/datastation/status"


def _tok(email: str, apps: list[str], rol: str = "ORG_USER") -> dict:
    token = central_token({
        "sub": "bbbbbbbb-0000-0000-0000-000000000001",
        "email": email,
        "role": rol,
        "tenant_name": "Lokaalbeheer Tenant",
        "apps": apps,
    })
    return {"Authorization": f"Bearer {token}"}


def _maak_gebruiker(email: str, *, actief: bool, wachtwoord: str | None = None) -> None:
    """Zet een gebruiker rechtstreeks in de lokale tabel, zoals het scherm dat deed."""
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).first()
        if tenant is None:
            tenant = Tenant(slug="lokaalbeheer", name="Lokaalbeheer Tenant", is_active=True)
            db.add(tenant); db.flush()
        bestaand = db.query(User).filter(User.email == email).first()
        if bestaand:
            db.delete(bestaand); db.flush()
        db.add(User(
            tenant_id=tenant.id, email=email, full_name="Testgebruiker",
            password_hash=hash_password(wachtwoord) if wachtwoord else None,
            role=UserRole.ORG_USER, is_active=actief,
        ))
        db.commit()
    finally:
        db.close()


def _is_actief(email: str) -> bool:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first().is_active
    finally:
        db.close()


# ── Waarom 'Wachtwoord' en 'Nieuwe gebruiker' uit het scherm konden ─────────

class TestLokaleWachtwoordrouteBlijftDicht:

    def test_lokale_login_staat_uit(self):
        assert local_login_enabled() is False, (
            "LOCAL_LOGIN_ENABLED staat aan; dan klopt de aanname onder deze wijziging niet meer"
        )

    def test_inloggen_met_een_lokaal_wachtwoord_wordt_geweigerd(self, client):
        """Ook mét het juiste wachtwoord komt er geen sessie uit deze applicatie.

        Een hier gezet wachtwoord is daarmee onbruikbaar — dat is de reden dat de
        knop 'Wachtwoord' uit het scherm is gehaald.
        """
        _maak_gebruiker("lokaal@test.rhadix.nl", actief=True,
                        wachtwoord="EenVoldoendeLangWachtwoord1!")
        res = client.post("/api/auth/login",
                          json={"email": "lokaal@test.rhadix.nl",
                                "password": "EenVoldoendeLangWachtwoord1!"})
        assert res.status_code == 403, res.text
        assert "SSO" in res.text


# ── De autorisatie is niet geraakt ──────────────────────────────────────────

class TestAutorisatieOngemoeid:

    def test_zonder_de_eigen_slug_weigert_de_beoordeling(self, client, monkeypatch):
        monkeypatch.setenv("APP_ACCESS_ENFORCE", "on")
        res = client.get(BESCHERMD, headers=_tok("zonderclaim@test.rhadix.nl", ["datavalidatie"]))
        assert res.status_code == 403, res.text

    def test_met_de_eigen_slug_wel_toegang(self, client, monkeypatch):
        monkeypatch.setenv("APP_ACCESS_ENFORCE", "on")
        res = client.get(BESCHERMD, headers=_tok("metclaim@test.rhadix.nl", ["datastation"]))
        assert res.status_code == 200, res.text

    def test_een_actieve_gebruiker_komt_gewoon_binnen(self, client):
        _maak_gebruiker("actief@test.rhadix.nl", actief=True)
        res = client.get("/api/auth/me", headers=_tok("actief@test.rhadix.nl", ["datastation"]))
        assert res.status_code == 200, res.text


# ── Vastgelegde afwijking, bewust NIET opgelost in deze wijziging ───────────

class TestBekendeAfwijking:
    """Lokaal deactiveren blokkeert een SSO-gebruiker niet.

    `get_current_user` past de `is_active`-filter alleen toe op het lokale HS256-pad.
    Een centraal RS256-token gaat rechtstreeks door JIT-provisioning, en die kijkt
    niet naar `is_active`. Omdat lokale login uitstaat, komt iederéén langs het
    centrale pad binnen — de knop 'Deactiveer' in dit scherm heeft dus geen effect
    op de toegang.

    Dit is geen gevolg van de schermwijziging; het gold al. Het herstellen ervan
    raakt de autorisatiebeslissing en is daarom apart gerapporteerd en niet in deze
    wijziging meegenomen. Deze tests leggen het huidige gedrag vast, zodat een
    latere correctie zichtbaar wordt in plaats van stilzwijgend te gebeuren.
    """

    def test_deactivering_houdt_stand_in_de_database(self, client):
        """JIT heractiveert de gebruiker in elk geval niet — de vlag blijft staan."""
        _maak_gebruiker("blijftdicht@test.rhadix.nl", actief=False)
        client.get("/api/auth/me", headers=_tok("blijftdicht@test.rhadix.nl", ["datastation"]))
        assert _is_actief("blijftdicht@test.rhadix.nl") is False, "JIT heeft de gebruiker geheractiveerd"

    def test_maar_de_gedeactiveerde_gebruiker_komt_er_via_sso_toch_in(self, client):
        """Vastgelegd huidig gedrag. Wordt dit ooit hersteld naar 401, pas deze test
        dan bewust aan — dat is precies de bedoeling van deze vastlegging."""
        _maak_gebruiker("geblokkeerd@test.rhadix.nl", actief=False)
        res = client.get("/api/auth/me", headers=_tok("geblokkeerd@test.rhadix.nl", ["datastation"]))
        assert res.status_code == 200, (
            "gedrag is gewijzigd: lokale deactivering blokkeert nu wél — werk deze "
            "vastlegging bij en meld het als opgelost"
        )
