import { useEffect, useState } from 'react'
import { Page, PageTitle, Card, BtnPrimary, BtnGhost, RoleBadge, Field, Modal } from '../components/UI'
import { listTenants, createTenant, listTenantUsers, platformStats } from '../services/api'

export default function Organisaties() {
  const [tenants, setTenants] = useState([])
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [showCreate, setShowCreate] = useState(false)
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
        sub="Beheer de organisaties op het Rhadix Uitvraag platform. Bij een nieuwe organisatie maakt u meteen de eerste organisatiebeheerder aan." />

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

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
        <BtnPrimary onClick={() => setShowCreate(true)}>+ Nieuwe organisatie</BtnPrimary>
      </div>

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

      {showCreate && <CreateTenantModal onClose={() => setShowCreate(false)} onDone={() => { setShowCreate(false); refresh() }} />}
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

function CreateTenantModal({ onClose, onDone }) {
  const [f, setF] = useState({ name: '', slug: '', admin_full_name: '', admin_email: '', admin_password: '' })
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const set = (k) => (v) => setF(p => ({ ...p, [k]: k === 'slug' ? v.toLowerCase().replace(/[^a-z0-9-]/g, '-') : v }))
  async function submit() {
    setBusy(true); setErr('')
    try { await createTenant(f); onDone() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Modal title="Nieuwe organisatie" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Organisatienaam" required value={f.name} onChange={set('name')} placeholder="Zorgorganisatie West" />
        <Field label="Slug (technische naam)" required value={f.slug} onChange={set('slug')} placeholder="zorgorg-west" />
        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.4px' }}>Eerste organisatiebeheerder</div>
        <Field label="Naam beheerder" value={f.admin_full_name} onChange={set('admin_full_name')} placeholder="Org Beheerder" />
        <Field label="E-mail beheerder" type="email" required value={f.admin_email} onChange={set('admin_email')} placeholder="beheer@organisatie.nl" />
        <Field label="Wachtwoord beheerder" type="password" required value={f.admin_password} onChange={set('admin_password')} placeholder="min. 12 tekens" />
        {err && <div style={{ color: 'var(--red)', fontSize: 13 }}>{err}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
          <BtnGhost onClick={onClose}>Annuleren</BtnGhost>
          <BtnPrimary onClick={submit} disabled={busy}>{busy ? 'Bezig…' : 'Aanmaken'}</BtnPrimary>
        </div>
      </div>
    </Modal>
  )
}
