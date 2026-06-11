import { useState } from 'react'
import { UitvraagLogo, UitvraagMark } from '../components/Brand'

// "Home" = het Rhadix-applicatieportaal.
const PORTAL_URL = 'https://app.rhadix.nl'

export default function LoginScreen({ onLogin }) {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [showForgot, setShowForgot] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await onLogin(email.trim(), password)
    } catch (err) {
      setError(err.message || 'Inloggen mislukt')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    padding: '10px 14px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)',
    fontSize: 14, fontFamily: 'var(--font)', outline: 'none', background: '#fff',
    transition: 'border-color .15s',
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'stretch', background: 'var(--bg)' }}>

      {/* ── Links — branding ── */}
      <div style={{
        flex: 1, background: 'var(--blue-hero)', display: 'flex', flexDirection: 'column',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Logo linksboven — klikbaar, terug naar het portaal */}
        <div style={{ padding: '32px 48px 0', flexShrink: 0 }}>
          <UitvraagLogo onClick={() => { window.location.href = PORTAL_URL }} />
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '0 48px 100px' }}>
          <span style={{
            display: 'inline-flex', alignSelf: 'flex-start', background: 'rgba(111,168,208,.25)',
            color: 'rgba(168,197,224,.95)', fontSize: 11, fontWeight: 700, letterSpacing: '1.5px',
            padding: '5px 12px', borderRadius: 99, marginBottom: 24, textTransform: 'uppercase',
          }}>Rhadix Datastation · KIK-V</span>
          <h1 style={{ fontWeight: 800, fontSize: 36, color: '#fff', lineHeight: 1.2, letterSpacing: '-0.02em', marginBottom: 18, maxWidth: 460 }}>
            Brondata, lokaal berekend tot{' '}
            <span style={{ color: 'var(--accent)' }}>gevalideerde antwoorden</span>
          </h1>
          <p style={{ fontSize: 15, color: 'rgba(168,197,224,.8)', lineHeight: 1.65, maxWidth: 420 }}>
            Brondata wordt afgebeeld op KIK-V-concepten (RDF) en gevalideerde vragen worden lokaal berekend — de data verlaat de bron niet.
          </p>
        </div>
        <div style={{ position: 'absolute', bottom: -40, right: -30, opacity: 0.12, transform: 'scale(7)' }}>
          <UitvraagMark size={40} />
        </div>
      </div>

      {/* ── Rechts — loginform ── */}
      <div style={{ width: 440, background: '#fff', display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '56px 48px', borderLeft: '1px solid var(--border)' }}>
        <div style={{ marginBottom: 28 }}>
          <h2 style={{ fontSize: 24, fontWeight: 800, color: 'var(--text)', marginBottom: 6 }}>Inloggen</h2>
          <p style={{ fontSize: 14, color: 'var(--text3)' }}>Voer uw e-mailadres en wachtwoord in.</p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)' }}>E-mailadres</span>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus
              placeholder="naam@organisatie.nl" style={inputStyle}
              onFocus={e => e.target.style.borderColor = 'var(--blue)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'} />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text2)' }}>Wachtwoord</span>
              <button type="button" onClick={() => setShowForgot(v => !v)} style={{
                fontSize: 12, color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer',
                padding: 0, fontFamily: 'var(--font)', textDecoration: showForgot ? 'none' : 'underline',
              }}>Wachtwoord vergeten?</button>
            </div>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
              placeholder="••••••••••••" style={inputStyle}
              onFocus={e => e.target.style.borderColor = 'var(--blue)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'} />
          </label>

          {showForgot && (
            <div style={{ padding: '12px 14px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 'var(--radius)', fontSize: 13, color: '#1d4ed8', lineHeight: 1.55 }}>
              <strong>Wachtwoord vergeten?</strong><br />
              Neem contact op met de beheerder van uw organisatie. Die kan via het beheerpaneel een nieuw wachtwoord voor u instellen.
            </div>
          )}

          {error && (
            <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 'var(--radius)', fontSize: 13, color: '#dc2626' }}>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} style={{
            marginTop: 4, padding: '12px 0', borderRadius: 'var(--radius)',
            background: loading ? 'var(--text3)' : 'var(--blue)', color: '#fff', border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer', fontSize: 15, fontWeight: 700,
            fontFamily: 'var(--font)', transition: 'background .15s',
          }}>{loading ? 'Bezig met inloggen…' : 'Inloggen →'}</button>
        </form>

        <p style={{ marginTop: 32, fontSize: 12, color: 'var(--text3)', textAlign: 'center', lineHeight: 1.6 }}>
          Geen account? Neem contact op met uw Rhadix-beheerder.
        </p>
        <p style={{ marginTop: 12, fontSize: 11, color: 'var(--text3)', textAlign: 'center' }}>
          <a href={PORTAL_URL} style={{ color: 'var(--text3)', textDecoration: 'underline' }}>← Terug naar het portaal</a>
        </p>
      </div>
    </div>
  )
}
