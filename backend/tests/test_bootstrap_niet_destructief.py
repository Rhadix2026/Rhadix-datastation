"""De startup-bootstrap mag geen gebruikers wissen.

Tot voor kort voerde `_seed_platform_admin` bij elke start
`TRUNCATE TABLE users RESTART IDENTITY CASCADE` uit. Daardoor verdween bij iedere
deploy of herstart de volledige gebruikerstabel, inclusief de accounts die via SSO
just-in-time waren aangemaakt. Deze tests leggen vast dat dat niet meer gebeurt.

`init_db()` is precies wat bij startup draait, dus die opnieuw aanroepen simuleert
een herstart/deployment op dezelfde database.
"""
from app.bootstrap import init_db, _ensure_platform_tenant
from app.database import SessionLocal
from app.models.auth_models import Tenant, User, UserRole

from tests._testkeys import central_token
from tests.conftest import SSO_ADMIN_EMAIL


def _users_count() -> int:
    db = SessionLocal()
    try:
        return db.query(User).count()
    finally:
        db.close()


def _get_user(email: str):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()


def test_jit_gebruiker_overleeft_herstart(client, auth):
    """Kern van deze reparatie: een SSO-gebruiker blijft na een herstart bestaan."""
    client.get("/api/auth/me", headers=auth)          # JIT-provisioning
    before = _get_user(SSO_ADMIN_EMAIL)
    assert before is not None
    user_id, tenant_id = before.id, before.tenant_id

    init_db()                                          # simuleert deploy/herstart

    after = _get_user(SSO_ADMIN_EMAIL)
    assert after is not None, "JIT-gebruiker is bij de herstart verdwenen"
    assert after.id == user_id, "gebruiker is opnieuw aangemaakt i.p.v. behouden"
    assert after.tenant_id == tenant_id
    assert after.role == UserRole.PLATFORM_ADMIN


def test_meerdere_gebruikers_overleven_herstart(client, auth):
    """Ook gebruikers die niet de beheerder zijn blijven staan."""
    for n in (1, 2, 3):
        token = central_token({
            "sub": f"3333333{n}-3333-3333-3333-333333333333",
            "email": f"medewerker{n}@test.rhadix.nl",
            "role": "ORG_USER",
            "tenant_name": "Zorgaanbieder Test",
        })
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    count_before = _users_count()
    assert count_before >= 4                            # 3 medewerkers + beheerder(s)

    init_db()

    assert _users_count() >= count_before, "de gebruikerstabel is gekrompen na een herstart"
    for n in (1, 2, 3):
        assert _get_user(f"medewerker{n}@test.rhadix.nl") is not None


def test_bootstrap_bevat_geen_truncate_of_delete():
    """Regressiebescherming op broncodeniveau: geen destructieve statements meer."""
    import inspect as _inspect
    import app.bootstrap as bootstrap

    bron = _inspect.getsource(bootstrap)
    # docstrings mogen het woord noemen; uitvoerbare statements niet
    regels = [r.strip() for r in bron.splitlines()
              if ("TRUNCATE" in r.upper() or "DELETE FROM" in r.upper())
              and not r.strip().startswith("#")
              and "`" not in r]
    assert regels == [], f"destructieve statement aangetroffen: {regels}"


def test_platform_tenant_blijft_geborgd():
    """De tenant-bootstrap die functioneel nodig is, blijft werken."""
    tenant_id = _ensure_platform_tenant()
    assert tenant_id is not None

    init_db()

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "platform").first()
        assert tenant is not None
        assert tenant.id == tenant_id, "platform-tenant is opnieuw aangemaakt i.p.v. hergebruikt"
    finally:
        db.close()


def test_jit_maakt_nieuwe_gebruiker_ook_na_herstart(client):
    """Na een herstart moet JIT-provisioning nog gewoon nieuwe gebruikers aanmaken."""
    init_db()
    token = central_token({
        "sub": "44444444-4444-4444-4444-444444444444",
        "email": "na-herstart@test.rhadix.nl",
        "role": "ORG_ADMIN",
        "tenant_name": "Zorgaanbieder Test",
    })
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert _get_user("na-herstart@test.rhadix.nl") is not None


# ── Bootstrap raakt gebruikers in het geheel niet meer ───────────────────────
def test_bootstrap_maakt_geen_gebruikers_aan(client, auth):
    """Een herstart voegt geen enkel account toe — ook geen bootstrap-admin."""
    client.get("/api/auth/me", headers=auth)          # zorg voor een JIT-gebruiker
    voor = _users_count()

    init_db()

    assert _users_count() == voor, "de bootstrap heeft accounts toegevoegd of verwijderd"


def test_bootstrap_reset_geen_wachtwoorden(client, auth):
    """Een herstart raakt wachtwoord-hashes niet aan.

    Eerder zette de bootstrap bij elke start het in de code gebakken wachtwoord op
    het adminaccount. Dat is verwijderd; een bestaande hash blijft nu ongemoeid.
    """
    from app.auth.security import hash_password
    from app.models.auth_models import UserRole

    db = SessionLocal()
    try:
        bestaand = User(email="handmatig@test.rhadix.nl", full_name="Handmatig account",
                        password_hash=hash_password("EenEigenWachtwoord1!"),
                        role=UserRole.ORG_ADMIN, is_active=True,
                        tenant_id=_ensure_platform_tenant())
        db.add(bestaand)
        db.commit()
        hash_voor = bestaand.password_hash
        rol_voor = bestaand.role
    finally:
        db.close()

    init_db()

    na = _get_user("handmatig@test.rhadix.nl")
    assert na is not None, "een bestaand account is verdwenen"
    assert na.password_hash == hash_voor, "de bootstrap heeft een wachtwoord gereset"
    assert na.role == rol_voor, "de bootstrap heeft een rol gewijzigd"


def test_bootstrap_bevat_geen_wachtwoordlogica():
    """Broncodecontrole: geen hardcoded wachtwoorden of admin-env meer."""
    import inspect as _inspect

    import app.bootstrap as bootstrap

    bron = _inspect.getsource(bootstrap)
    for term in ("hash_password", "KIK_ADMIN_PASSWORD", "RHADIX_ADMIN_PASSWORD", "AUTH_RESET"):
        regels = [r.strip() for r in bron.splitlines()
                  if term in r and not r.strip().startswith("#") and '"""' not in r]
        assert regels == [], f"{term} nog aanwezig in bootstrap: {regels}"
