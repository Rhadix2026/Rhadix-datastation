/**
 * Gebruikersbeheer — overzicht van de gebruikers van uw organisatie in deze applicatie.
 *
 * Dit scherm heeft bewust geen bewerkacties meer. Identiteit en applicatietoegang
 * worden centraal beheerd in Rhadix Datavalidatie; wat hier staat is een afgeleide die
 * bij de eerste SSO-login vanzelf ontstaat.
 *
 * Wat er is weggehaald en waarom:
 *
 *   Nieuwe gebruiker  — leverde een account op dat nergens kon inloggen: de lokale
 *                       wachtwoordroute staat uit (LOCAL_LOGIN_ENABLED=0) en het
 *                       account bestaat centraal niet, dus krijgt het geen apps-claim.
 *   Wachtwoord        — zette een hash die nooit werd vergeleken, om diezelfde reden.
 *   Deactiveer        — had geen effect op de toegang. `get_current_user` past de
 *                       is_active-filter alleen toe op het lokale HS256-pad, terwijl
 *                       een centraal RS256-token rechtstreeks door JIT-provisioning
 *                       gaat. Omdat lokale login uitstaat, komt iedereen langs dat
 *                       centrale pad binnen.
 *   Verwijder         — was tijdelijk: JIT maakt de gebruiker bij de eerstvolgende
 *                       login opnieuw aan, actief en met een nieuw id.
 *
 * Alle vier blijven beschikbaar voor dezelfde rol in het centrale beheerscherm van
 * Rhadix Datavalidatie; daar hebben ze wél effect. Het daadwerkelijk verwijderen van
 * een gebruiker hoort daar thuis, omdat het de identiteit zelf weghaalt.
 *
 * NOG NIET OPGELOST: één gebruiker uit één applicatie weren kan hiermee niet. Dat is
 * geen omissie van dit scherm maar van het toewijzingsmodel — de apps-claim is de
 * vereniging van organisatie- en gebruikerstoewijzingen, waardoor een persoonlijke
 * intrekking geen effect heeft. Dat valt onder bevinding 8 van het bevindingenregister
 * en moet vanuit het centrale toewijzings-/autorisatiemodel worden opgelost.
 *
 * De endpoints achter de weggehaalde knoppen zijn in deze wijziging bewust blijven
 * staan; ze worden alleen niet meer aangeroepen. Het opruimen daarvan is een aparte
 * afweging.
 */
import { useEffect, useState } from 'react'
import { Page, PageTitle, Card, BtnGhost, RoleBadge, platformUrl } from '../components/UI'
import { listOrgUsers } from '../services/api'

export default function Gebruikersbeheer({ authUser }) {
  const [users, setUsers]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    let leeft = true
    listOrgUsers()
      .then(u => { if (leeft) setUsers(u) })
      .catch(e => { if (leeft) setError(e.message) })
      .finally(() => { if (leeft) setLoading(false) })
    return () => { leeft = false }
  }, [])

  return (
    <Page>
      <PageTitle badge={`Organisatie: ${authUser.tenant_name}`} title="Gebruikersbeheer"
        sub="Overzicht van de gebruikers van uw organisatie in deze applicatie. Accounts, wachtwoorden en applicatietoewijzingen worden centraal beheerd op het Rhadix-platform." />

      <Card style={{ marginBottom: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.5 }}>
          Een gebruiker aanmaken of verwijderen, een wachtwoord instellen of een applicatie
          toewijzen doet u op het Platform. Een nieuwe gebruiker verschijnt hier vanzelf na
          zijn eerste login.
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
              <th style={th}>Naam</th><th style={th}>E-mail</th><th style={th}>Rol</th><th style={th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={4} style={{ ...td, color: 'var(--text3)' }}>Laden…</td></tr>}
            {!loading && users.length === 0 && (
              <tr><td colSpan={4} style={{ ...td, color: 'var(--text3)' }}>
                Nog geen gebruikers. Ze verschijnen hier na hun eerste login.
              </td></tr>
            )}
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
