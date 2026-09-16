"""
test_beheerscherm_zonder_bewerkacties.py — het beheerscherm is een overzicht.

Afronding van bevinding 13. Het lokale gebruikersbeheer in deze applicatie bood
knoppen die niets opleverden. 'Nieuwe gebruiker' en 'Wachtwoord' waren al weg; met
deze wijziging vervallen ook 'Deactiveer' en 'Verwijder':

  Deactiveer  had geen effect op de toegang — `get_current_user` past de
              is_active-filter alleen toe op het lokale HS256-pad, terwijl een
              centraal RS256-token rechtstreeks door JIT-provisioning gaat.
  Verwijder   was tijdelijk: JIT maakt de gebruiker bij de eerstvolgende login
              opnieuw aan, actief en met een nieuw id.

De endpoints blijven in deze wijziging bewust staan; alleen het scherm roept ze niet
meer aan. Deze suite bewaakt daarom twee dingen tegelijk: dat de knoppen weg zijn en
weg blijven, én dat er verder niets is verschoven — rollen, rechten, de apps-claim en
de SSO-afhandeling zijn ongemoeid.

NOG NIET OPGELOST, bewust: één gebruiker uit één applicatie weren. Dat kan niet via
dit scherm en ook niet centraal, omdat de apps-claim de vereniging is van organisatie-
en gebruikerstoewijzingen. Het valt onder bevinding 8 en hoort vanuit het centrale
toewijzings-/autorisatiemodel te worden opgelost.
"""
from pathlib import Path

import pytest

from app.auth.app_access import APP_SLUG, enforce_mode
from app.auth.router import local_login_enabled
from app.models.auth_models import UserRole

from tests._testkeys import central_token

SCHERM = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "Gebruikersbeheer.jsx"
BESCHERMD = "/api/datastation/status"


@pytest.fixture(scope="module")
def broncode() -> str:
    assert SCHERM.exists(), f"beheerscherm niet gevonden op {SCHERM}"
    return SCHERM.read_text(encoding="utf-8")


def _tok(email: str, apps: list[str], rol: str = "ORG_USER") -> dict:
    return {"Authorization": "Bearer " + central_token({
        "sub": "cccccccc-0000-0000-0000-000000000001",
        "email": email, "role": rol,
        "tenant_name": "Beheerscherm Tenant", "apps": apps,
    })}


# ── De knoppen zijn weg en blijven weg ──────────────────────────────────────

class TestGeenBewerkactiesMeer:
    """Broncontrole op het scherm zelf: JSX is niet uitvoerbaar in pytest, maar of
    een knop en zijn aanroep erin staan is prima leesbaar — en dat is precies wat
    een regressie hier zou zijn."""

    @pytest.mark.parametrize("aanroep", [
        "toggleUser",      # Deactiveer / Activeer
        "deleteOrgUser",   # Verwijder
        "createOrgUser",   # Nieuwe gebruiker (eerdere ronde)
        "resetUserPwd",    # Wachtwoord (eerdere ronde)
    ])
    def test_scherm_roept_geen_bewerkactie_meer_aan(self, broncode, aanroep):
        assert aanroep not in broncode, (
            f"{aanroep} wordt weer aangeroepen vanuit het beheerscherm; "
            "bewerkacties horen centraal in Rhadix Datavalidatie"
        )

    @pytest.mark.parametrize("label", ["Deactiveer", "Activeer", "Verwijder",
                                       "Nieuwe gebruiker", "Wachtwoord"])
    def test_knop_staat_niet_meer_in_het_scherm(self, broncode, label):
        # De toelichting bovenaan het bestand benoemt de weggehaalde knoppen; die
        # tekst telt niet mee.
        zonder_toelichting = broncode.split("*/", 1)[-1]
        assert label not in zonder_toelichting, f"knop '{label}' staat weer in het scherm"

    def test_het_overzicht_zelf_blijft(self, broncode):
        assert "listOrgUsers" in broncode, "het scherm toont geen gebruikers meer"

    def test_verwijst_naar_het_centrale_beheer(self, broncode):
        assert "platformUrl" in broncode, "de verwijzing naar het Platform ontbreekt"


# ── De endpoints blijven bestaan; alleen het scherm gebruikt ze niet ────────

class TestEndpointsOngemoeid:
    """Bewust niet opgeruimd in deze wijziging, zodat hij klein en testbaar blijft."""

    @pytest.mark.parametrize("methode,pad", [
        ("PATCH",  "/api/org/users/{id}/deactivate"),
        ("DELETE", "/api/org/users/{id}"),
    ])
    def test_endpoint_bestaat_nog(self, client, methode, pad):
        from app.main import app
        paden = {r.path for r in app.routes}
        assert pad.replace("{id}", "{user_id}") in paden, f"{methode} {pad} is verdwenen"

    def test_endpoint_blijft_afgeschermd_zonder_sessie(self, client):
        res = client.delete("/api/org/users/00000000-0000-0000-0000-000000000001")
        assert res.status_code in (401, 403), res.text


# ── Rollen, rechten en autorisatie ongewijzigd ──────────────────────────────

class TestRechtenOngewijzigd:

    def test_de_org_router_vereist_dezelfde_rollen(self):
        from app.routers import org
        # Vastgelegd: organisatiebeheer is voorbehouden aan ORG_ADMIN en PLATFORM_ADMIN.
        assert org._org_admin is not None
        bron = Path(org.__file__).read_text(encoding="utf-8")
        assert "require_role(UserRole.ORG_ADMIN, UserRole.PLATFORM_ADMIN)" in bron

    def test_een_gewone_gebruiker_komt_niet_bij_organisatiebeheer(self, client):
        res = client.get("/api/org/users", headers=_tok("gewoon@test.rhadix.nl", ["datastation"]))
        assert res.status_code == 403, res.text

    def test_een_beheerder_komt_er_wel_bij(self, client):
        res = client.get("/api/org/users",
                         headers=_tok("beheer@test.rhadix.nl", ["datastation"], rol="ORG_ADMIN"))
        assert res.status_code == 200, res.text

    def test_rolwaarden_zijn_ongewijzigd(self):
        assert {r.value for r in UserRole} >= {"ORG_USER", "ORG_ADMIN", "PLATFORM_ADMIN"}


class TestAutorisatiemodelOngewijzigd:
    """APP_ACCESS_ENFORCE, de apps-claim en SSO zijn niet geraakt."""

    def test_de_eigen_slug_is_ongewijzigd(self):
        assert APP_SLUG == "datastation"

    def test_de_standen_van_enforce_zijn_ongewijzigd(self, monkeypatch):
        monkeypatch.delenv("APP_ACCESS_ENFORCE", raising=False)
        assert enforce_mode() == "warn", "de veilige standaardstand is gewijzigd"
        for stand in ("off", "warn", "on"):
            monkeypatch.setenv("APP_ACCESS_ENFORCE", stand)
            assert enforce_mode() == stand
        monkeypatch.setenv("APP_ACCESS_ENFORCE", "onzin")
        assert enforce_mode() == "warn", "een onbekende waarde valt niet meer veilig terug"

    def test_lokale_login_blijft_dicht(self):
        assert local_login_enabled() is False

    def test_zonder_de_eigen_slug_geen_toegang(self, client, monkeypatch):
        monkeypatch.setenv("APP_ACCESS_ENFORCE", "on")
        res = client.get(BESCHERMD, headers=_tok("zonderslug@test.rhadix.nl", ["datavalidatie"]))
        assert res.status_code == 403, res.text

    def test_met_de_eigen_slug_wel_toegang(self, client, monkeypatch):
        monkeypatch.setenv("APP_ACCESS_ENFORCE", "on")
        res = client.get(BESCHERMD, headers=_tok("metslug@test.rhadix.nl", ["datastation"]))
        assert res.status_code == 200, res.text

    def test_sso_provisioning_werkt_ongewijzigd(self, client):
        """Een onbekend e-mailadres levert nog steeds een JIT-gebruiker op."""
        res = client.get("/api/auth/me", headers=_tok("nieuw-via-sso@test.rhadix.nl", ["datastation"]))
        assert res.status_code == 200, res.text
        assert res.json()["email"] == "nieuw-via-sso@test.rhadix.nl"
