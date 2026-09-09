/**
 * Gebruikersbeheer — toegang tot DEZE applicatie, per gebruiker.
 *
 * Accounts en applicatietoegang worden centraal beheerd in Rhadix Datavalidatie: daar
 * worden gebruikers aangemaakt, wachtwoorden gezet en applicaties toegewezen. Deze
 * applicatie kent alleen een lokale afgeleide, die bij de eerste SSO-login vanzelf
 * ontstaat.
 *
 * Dit scherm bood eerder ook 'Nieuwe gebruiker' en 'Wachtwoord'. Beide leverden niets
 * bruikbaars op: de lokale wachtwoordroute staat uit (LOCAL_LOGIN_ENABLED=0), en een
 * hier aangemaakt account bestaat centraal niet en krijgt dus geen apps-claim. Ze zijn
 * weggehaald omdat ze een verwachting wekten die ze niet waarmaakten — niet om de
 * schermen op elkaar te laten lijken. Beide functies blijven onverkort beschikbaar
 * voor dezelfde rol in het centrale beheerscherm.
 *
 * (De)activeren en verwijderen zijn ongewijzigd gebleven. LET OP: tijdens de analyse
 * bleek dat lokaal deactiveren een SSO-gebruiker niet blokkeert — `get_current_user`
 * past de is_active-filter alleen toe op het lokale HS256-pad, terwijl een centraal
 * RS256-token rechtstreeks door JIT-provisioning gaat. Dat is apart gerapporteerd en
 * bewust niet in deze wijziging opgelost, omdat het de autorisatiebeslissing raakt.
 * Zie backend/tests/test_lokaal_gebruikersbeheer.py, TestBekendeAfwijking.
 */
import { useEffect, useState } from 'react'
import { Page, PageTitle, Card, BtnGhost, RoleBadge, platformUrl } from '../components/UI'
import { listOrgUsers, toggleUser, deleteOrgUser } from '../services/api'

export default function Gebruikersbeheer({ authUser }) {
  const [users, setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState('')

  async function refresh() {
    setLoading(true); setError('')
    try { setUsers(await listOrgUsers()) }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [])

  async function onToggle(u) {
    try { await toggleUser(u.id); refresh() } catch (e) { alert(e.message) }
  }
  async function onDelete(u) {
    if (!confirm(`Gebruiker ${u.email} verwijderen uit deze applicatie?`)) return
    try { await deleteOrgUser(u.id); refresh() } catch (e) { alert(e.message) }
  }

  return (
    <Page>
      <PageTitle badge={`Organisatie: ${authUser.tenant_name}`} title="Gebruikersbeheer"
        sub="Overzicht van de gebruikers van uw organisatie in deze applicatie. Accounts, wachtwoorden en applicatietoewijzingen worden centraal beheerd op het Rhadix-platform." />

      <Card style={{ marginBottom: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>
          Een gebruiker aanmaken, een wachtwoord instellen of een applicatie toewijzen doet u
          op het Platform. Een nieuwe gebruiker verschijnt hier vanzelf na zijn eerste login.
        </div>
        <BtnGhost onClick={() => { window.location.href = platformUrl() }}>
          ▦ Naar het Platform
        </BtnGhost>
      </Card>

      {error && <Card style={{ marginBottom: 14, color: 'var(--red)', background: 'var(--red-bg)', border: '1px solid var(--red-light)' }}>{error}</Card>}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: 'var(--bg)', textAlign: 'left' }}>
              <th style={th}>Naam</th><th style={th}>E-mail</th><th style={th}>Rol</th>
              <th style={th}>Status</th><th style={{ ...th, textAlign: 'right' }}>Acties</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={5} style={{ ...td, color: 'var(--text3)' }}>Laden…</td></tr>}
            {!loading && users.length === 0 && <tr><td colSpan={5} style={{ ...td, color: 'var(--text3)' }}>Nog geen gebruikers. Ze verschijnen hier na hun eerste login.</td></tr>}
            {users.map(u => (
              <tr key={u.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={td}>{u.full_name || '—'}{u.id === authUser.id && <span style={{ fontSize: 11, color: 'var(--text4)' }}> (u)</span>}</td>
                <td style={{ ...td, color: 'var(--text2)' }}>{u.email}</td>
                <td style={td}><RoleBadge role={u.role} /></td>
                <td style={td}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: u.is_active ? 'var(--green)' : 'var(--text4)' }}>
                    {u.is_active ? '● Actief' : '○ Inactief'}
                  </span>
                </td>
                <td style={{ ...td, textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <BtnGhost onClick={() => onToggle(u)} disabled={u.id === authUser.id} style={{ marginRight: 6 }}>
                    {u.is_active ? 'Deactiveer' : 'Activeer'}
                  </BtnGhost>
                  <BtnGhost danger onClick={() => onDelete(u)} disabled={u.id === authUser.id}>Verwijder</BtnGhost>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Page>
  )
}

const th = { padding: '12px 16px', fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.4px' }
const td = { padding: '12px 16px' }
