import { useEffect, useState } from 'react'
import { Page, PageTitle, Card, BtnPrimary, BtnGhost, RoleBadge, Field, Modal } from '../components/UI'
import { listOrgUsers, createOrgUser, toggleUser, resetUserPwd, deleteOrgUser } from '../services/api'

export default function Gebruikersbeheer({ authUser }) {
  const [users, setUsers]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [resetFor, setResetFor]     = useState(null)

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
    if (!confirm(`Gebruiker ${u.email} verwijderen?`)) return
    try { await deleteOrgUser(u.id); refresh() } catch (e) { alert(e.message) }
  }

  return (
    <Page>
      <PageTitle badge={`Organisatie: ${authUser.tenant_name}`} title="Gebruikersbeheer"
        sub="Beheer de gebruikers binnen uw organisatie: aanmaken, rol toewijzen, (de)activeren en wachtwoorden opnieuw instellen." />

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
        <BtnPrimary onClick={() => setShowCreate(true)}>+ Nieuwe gebruiker</BtnPrimary>
      </div>

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
            {!loading && users.length === 0 && <tr><td colSpan={5} style={{ ...td, color: 'var(--text3)' }}>Nog geen gebruikers.</td></tr>}
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
                  <BtnGhost onClick={() => setResetFor(u)} style={{ marginRight: 6 }}>Wachtwoord</BtnGhost>
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

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} onDone={() => { setShowCreate(false); refresh() }} />}
      {resetFor && <ResetPasswordModal user={resetFor} onClose={() => setResetFor(null)} onDone={() => setResetFor(null)} />}
    </Page>
  )
}

const th = { padding: '12px 16px', fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.4px' }
const td = { padding: '12px 16px' }

function CreateUserModal({ onClose, onDone }) {
  const [f, setF] = useState({ full_name: '', email: '', password: '', role: 'ORG_USER' })
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  const set = (k) => (v) => setF(p => ({ ...p, [k]: v }))
  async function submit() {
    setBusy(true); setErr('')
    try { await createOrgUser(f); onDone() }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Modal title="Nieuwe gebruiker" onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Volledige naam" value={f.full_name} onChange={set('full_name')} placeholder="Jan Jansen" />
        <Field label="E-mailadres" type="email" required value={f.email} onChange={set('email')} placeholder="naam@organisatie.nl" />
        <Field label="Wachtwoord" type="password" required value={f.password} onChange={set('password')} placeholder="min. 12 tekens" />
        <Field label="Rol" value={f.role} onChange={set('role')} options={[
          { value: 'ORG_USER', label: 'Gebruiker' },
          { value: 'ORG_ADMIN', label: 'Organisatiebeheerder' },
        ]} />
        <div style={{ fontSize: 12, color: 'var(--text3)' }}>Wachtwoord: min. 12 tekens, met hoofd-/kleine letter, cijfer en speciaal teken.</div>
        {err && <div style={{ color: 'var(--red)', fontSize: 13 }}>{err}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
          <BtnGhost onClick={onClose}>Annuleren</BtnGhost>
          <BtnPrimary onClick={submit} disabled={busy}>{busy ? 'Bezig…' : 'Aanmaken'}</BtnPrimary>
        </div>
      </div>
    </Modal>
  )
}

function ResetPasswordModal({ user, onClose, onDone }) {
  const [pwd, setPwd] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('')
  async function submit() {
    setBusy(true); setErr('')
    try { await resetUserPwd(user.id, pwd); alert(`Wachtwoord van ${user.email} is bijgewerkt.`); onDone() }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  return (
    <Modal title={`Wachtwoord opnieuw instellen`} onClose={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ fontSize: 13, color: 'var(--text2)' }}>Voor: <strong>{user.email}</strong></div>
        <Field label="Nieuw wachtwoord" type="password" required value={pwd} onChange={setPwd} placeholder="min. 12 tekens" />
        {err && <div style={{ color: 'var(--red)', fontSize: 13 }}>{err}</div>}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <BtnGhost onClick={onClose}>Annuleren</BtnGhost>
          <BtnPrimary onClick={submit} disabled={busy}>{busy ? 'Bezig…' : 'Instellen'}</BtnPrimary>
        </div>
      </div>
    </Modal>
  )
}
