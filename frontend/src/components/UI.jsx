import { Link, useNavigate } from 'react-router-dom'
import { UitvraagLogo } from './Brand'
import { currentBrand, toggleBrand } from '../brand'

// Terug-naar-platform: naar het portaal 'kies een applicatie' (env-afhankelijk).
function _platformUrl() {
  if (import.meta.env.VITE_PLATFORM_URL) return import.meta.env.VITE_PLATFORM_URL
  const stag = typeof location !== 'undefined' && location.hostname.includes('staging')
  return stag ? 'https://app-staging.rhadix.nl' : 'https://app.rhadix.nl'
}


// ─── Nav ─────────────────────────────────────────────────────────────────────
export function Nav({ authUser, onLogout, links = [] }) {
  const navigate = useNavigate()
  return (
    <header style={{
      background: 'var(--blue-hero)', borderBottom: '1px solid rgba(255,255,255,.08)',
      padding: '0 32px', height: 64, display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100,
      boxShadow: '0 2px 12px rgba(0,0,0,.25)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <UitvraagLogo onClick={() => navigate('/')} />
        <button onClick={() => navigate(-1)} title="Terug" style={{
          background: 'rgba(255,255,255,.22)', border: '1.5px solid rgba(255,255,255,.7)',
          borderRadius: 'var(--radius)', padding: '5px 14px', cursor: 'pointer',
          fontSize: 13, color: '#fff', fontFamily: 'var(--font)', fontWeight: 700,
          letterSpacing: '.03em', display: 'flex', alignItems: 'center', gap: 4,
        }}>← Terug</button>
        <button onClick={() => { window.location.href = _platformUrl() }} title="Terug naar platform — kies een applicatie" style={{
          background: 'rgba(255,255,255,.1)', border: '1px solid rgba(255,255,255,.28)',
          borderRadius: 'var(--radius)', padding: '5px 12px', cursor: 'pointer',
          fontSize: 12.5, color: '#fff', fontFamily: 'var(--font)', fontWeight: 700,
          letterSpacing: '.02em', display: 'flex', alignItems: 'center', gap: 5,
        }}>▦ Platform</button>
        {import.meta.env.VITE_KIK_ENV === 'staging' && (
          <button onClick={toggleBrand} title="White-label demo (alleen staging)" style={{
            background: 'rgba(255,255,255,.12)', border: '1px solid rgba(255,255,255,.35)',
            borderRadius: 99, padding: '5px 14px', cursor: 'pointer',
            fontSize: 12.5, color: '#fff', fontFamily: 'var(--font)', fontWeight: 700,
          }}>{currentBrand() === 'kikv' ? '← Rhadix' : 'KIK-V ↗'}</button>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {links.map(l => (
          <Link key={l.to} to={l.to} style={_navBtn}>{l.label}</Link>
        ))}
        {authUser && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 30, height: 30, borderRadius: '50%',
              background: 'rgba(255,255,255,.15)', border: '1.5px solid rgba(255,255,255,.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700, color: '#fff',
            }}>{(authUser.name || authUser.email || '?')[0].toUpperCase()}</div>
            <span style={{ fontSize: 13, color: 'rgba(255,255,255,.8)', fontWeight: 500 }}>
              {authUser.name || authUser.email}
            </span>
            {onLogout && (
              <button onClick={onLogout} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'rgba(255,255,255,.6)', fontSize: 13, fontFamily: 'var(--font)', padding: '4px 0',
              }}>Uitloggen</button>
            )}
          </div>
        )}
      </div>
    </header>
  )
}

const _navBtn = {
  background: 'rgba(255,255,255,.08)', border: '1px solid rgba(255,255,255,.15)',
  borderRadius: 'var(--radius)', padding: '6px 12px',
  color: 'rgba(255,255,255,.85)', fontSize: 13, fontWeight: 600,
  fontFamily: 'var(--font)', letterSpacing: '.02em',
}

export function Page({ children }) {
  return <div className="page-container">{children}</div>
}

export function PageTitle({ title, sub, badge }) {
  return (
    <div style={{ marginBottom: 28 }}>
      {badge && (
        <div style={{
          display: 'inline-flex', alignItems: 'center', background: 'var(--blue-light)',
          color: 'var(--blue)', fontSize: 12, fontWeight: 600, padding: '4px 12px',
          borderRadius: 20, marginBottom: 12,
        }}>{badge}</div>
      )}
      <h1 style={{ fontSize: 28, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em', marginBottom: 6 }}>{title}</h1>
      {sub && <p style={{ fontSize: 14, color: 'var(--text3)', lineHeight: 1.5, maxWidth: 680 }}>{sub}</p>}
    </div>
  )
}

export function Card({ children, style = {}, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)',
      padding: '20px 24px', boxShadow: 'var(--shadow)', cursor: onClick ? 'pointer' : undefined,
      transition: 'box-shadow .15s, transform .15s', ...style,
    }}>{children}</div>
  )
}

export function BtnPrimary({ children, onClick, disabled, type = 'button', style: sx = {} }) {
  return (
    <button type={type} onClick={disabled ? undefined : onClick} disabled={disabled} style={{
      background: disabled ? 'var(--k-blue-mid)' : 'var(--blue)', color: '#fff', border: 'none',
      borderRadius: 'var(--radius)', padding: '10px 20px', fontSize: 14, fontWeight: 600,
      cursor: disabled ? 'not-allowed' : 'pointer', fontFamily: 'var(--font)',
      display: 'inline-flex', alignItems: 'center', gap: 6, transition: 'background .15s', ...sx,
    }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.background = 'var(--blue-dark)' }}
      onMouseLeave={e => { if (!disabled) e.currentTarget.style.background = 'var(--blue)' }}
    >{children}</button>
  )
}

export function StatusDot({ ok, label }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text3)' }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: ok ? 'var(--green)' : 'var(--red)' }} />
      {label}
    </span>
  )
}

// ─── Extra UI-helpers voor gebruikersbeheer ──────────────────────────────────
export function BtnGhost({ children, onClick, disabled, danger, style: sx = {} }) {
  return (
    <button type="button" onClick={disabled ? undefined : onClick} disabled={disabled} style={{
      background: '#fff', color: danger ? 'var(--red)' : 'var(--text2)',
      border: `1px solid ${danger ? 'var(--red-light)' : 'var(--border2)'}`,
      borderRadius: 'var(--radius)', padding: '6px 12px', fontSize: 13, fontWeight: 600,
      cursor: disabled ? 'not-allowed' : 'pointer', fontFamily: 'var(--font)',
      opacity: disabled ? 0.5 : 1, ...sx,
    }}>{children}</button>
  )
}

export function RoleBadge({ role }) {
  const map = {
    PLATFORM_ADMIN: { label: 'Platformbeheerder', bg: '#1A2847', fg: '#fff' },
    ORG_ADMIN:      { label: 'Organisatiebeheerder', bg: 'var(--blue-light)', fg: 'var(--blue)' },
    ORG_USER:       { label: 'Gebruiker', bg: 'var(--bg)', fg: 'var(--text3)' },
  }
  const c = map[role] || map.ORG_USER
  return <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 99, background: c.bg, color: c.fg }}>{c.label}</span>
}

export function Field({ label, type = 'text', value, onChange, placeholder, required, options }) {
  const base = { padding: '9px 12px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 14, fontFamily: 'var(--font)', outline: 'none', width: '100%', background: '#fff' }
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)' }}>{label}{required && <span style={{ color: 'var(--red)' }}> *</span>}</span>
      {options
        ? <select value={value} onChange={e => onChange(e.target.value)} style={base}>
            {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        : <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={base} />}
    </label>
  )
}

export function Modal({ title, children, onClose }) {
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(15,26,48,.45)', zIndex: 200,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: '#fff', borderRadius: 'var(--radius-lg)', width: 460, maxWidth: '100%',
        maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 50px rgba(0,0,0,.3)',
      }}>
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: 17, fontWeight: 700, color: 'var(--text)' }}>{title}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: 'var(--text3)' }}>×</button>
        </div>
        <div style={{ padding: 22 }}>{children}</div>
      </div>
    </div>
  )
}

// ─── Status-pil voor uitwisselprofiel-implementatie ──────────────────────────
export function StatusPill({ status }) {
  const map = {
    productie:     { bg: 'var(--green-light)', fg: 'var(--green)', label: 'Productie' },
    test:          { bg: 'var(--amber-light)', fg: 'var(--amber)', label: 'Test' },
    implementatie: { bg: 'var(--blue-light)',  fg: 'var(--blue)',  label: 'Implementatie' },
    uitgefaseerd:  { bg: 'var(--bg)',          fg: 'var(--text3)', label: 'Uitgefaseerd' },
  }
  const c = map[status] || map.uitgefaseerd
  return <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 9px', borderRadius: 99, background: c.bg, color: c.fg }}>{c.label}</span>
}
