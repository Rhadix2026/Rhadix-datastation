import { useEffect, useState } from 'react'
import { Page, PageTitle, Card, BtnGhost, RoleBadge } from '../components/UI'
import { listTenants, listTenantUsers, platformStats } from '../services/api'

export default function Organisaties() {
  const [tenants, setTenants] = useState([])
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [drill, setDrill]     = useState(null)   // tenant waarvan we users tonen

  async function refresh() {
    setLoading(true); setError('')
    try {
      const [t, s] = await Promise.all([listTenants(), platformStats()])
      setTenants(t); setStats(s)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }
  useEffect(() => { refresh() }, [])

  if (drill) return <TenantUsers tenant={drill} onBack={() => setDrill(null)} />

  return (
    <Page>
      <PageTitle badge="Platformbeheer" title="Organisaties"
        sub="Overzicht van de organisaties die deze applicatie gebruiken. Organisaties en hun gebruikers worden centraal aangemaakt op het Rhadix-platform en verschijnen hier na de eerste login." />

      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 20 }}>
          {[['Organisaties', stats.tenants], ['Gebruikers', stats.users], ['Actieve gebruikers', stats.active_users]].map(([l, v]) => (
            <div key={l} style={{ background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '18px 22px', boxShadow: 'var(--shadow)' }}>
              <div style={{ fontSize: 30, fontWeight: 800, color: 'var(--blue)' }}>{v}</div>
              <div style={{ fontSize: 13, color: 'var(--text3)' }}>{l}</div>
            </div>
          ))}
        </div>
      )}

      {error && <Card style={{ marginBottom: 14, color: 'var(--red)', background: 'var(--red-bg)', border: '1px solid var(--red-light)' }}>{error}</Card>}

      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: 'var(--bg)', textAlign: 'left' }}>
              <th style={th}>Organisatie</th><th style={th}>Slug</th><th style={th}>Gebruikers</th>
              <th style={th}>Status</th><th style={{ ...th, textAlign: 'right' }}>Acties</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={5} style={{ ...td, color: 'var(--text3)' }}>Laden…</td></tr>}
            {!loading && tenants.length === 0 && <tr><td colSpan={5} style={{ ...td, color: 'var(--text3)' }}>Nog geen organisaties.</td></tr>}
            {tenants.map(t => (
              <tr key={t.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={{ ...td, fontWeight: 600 }}>{t.name}</td>
                <td style={{ ...td, color: 'var(--text3)', fontFamily: 'monospace', fontSize: 12 }}>{t.slug}</td>
                <td style={td}>{t.user_count}</td>
                <td style={td}><span style={{ fontSize: 12, fontWeight: 600, color: t.is_active ? 'var(--green)' : 'var(--text4)' }}>{t.is_active ? '● Actief' : '○ Inactief'}</span></td>
                <td style={{ ...td, textAlign: 'right' }}><BtnGhost onClick={() => setDrill(t)}>Bekijk gebruikers</BtnGhost></td>
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

function TenantUsers({ tenant, onBack }) {
  const [users, setUsers] = useState([]); const [loading, setLoading] = useState(true)
  useEffect(() => { listTenantUsers(tenant.id).then(setUsers).finally(() => setLoading(false)) }, [tenant])
  return (
    <Page>
      <BtnGhost onClick={onBack} style={{ marginBottom: 16 }}>← Terug naar organisaties</BtnGhost>
      <PageTitle badge={`Slug: ${tenant.slug}`} title={tenant.name} sub="Gebruikers binnen deze organisatie." />
      <Card style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead><tr style={{ background: 'var(--bg)', textAlign: 'left' }}>
            <th style={th}>Naam</th><th style={th}>E-mail</th><th style={th}>Rol</th><th style={th}>Status</th>
          </tr></thead>
          <tbody>
            {loading && <tr><td colSpan={4} style={{ ...td, color: 'var(--text3)' }}>Laden…</td></tr>}
            {users.map(u => (
              <tr key={u.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={td}>{u.full_name || '—'}</td>
                <td style={{ ...td, color: 'var(--text2)' }}>{u.email}</td>
                <td style={td}><RoleBadge role={u.role} /></td>
                <td style={td}><span style={{ fontSize: 12, fontWeight: 600, color: u.is_active ? 'var(--green)' : 'var(--text4)' }}>{u.is_active ? '● Actief' : '○ Inactief'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Page>
  )
}
