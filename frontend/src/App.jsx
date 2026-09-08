import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Nav, platformUrl } from './components/UI'
import { login as apiLogin, getMe, clearAuthToken } from './services/api'
import { applyBranding } from './brand'
import LoginScreen      from './pages/LoginScreen'
import Home             from './pages/Home'
import Datastation      from './pages/Datastation'
import Gebruikersbeheer from './pages/Gebruikersbeheer'
import Organisaties     from './pages/Organisaties'
import NotFound         from './pages/NotFound'

const KIK_ENV = import.meta.env.VITE_KIK_ENV

function EnvBanner() {
  if (KIK_ENV !== 'staging') return null
  return (
    <div style={{ background: '#f59e0b', color: '#1a2847', textAlign: 'center', fontSize: 13, fontWeight: 700, padding: '6px 12px', letterSpacing: '.03em' }}>
      STAGING-OMGEVING — testdata, niet voor productiegebruik
    </div>
  )
}

function GeenAppToegang({ melding, onLogout }) {
  return (
    <div style={{ padding: 48, display: 'flex', justifyContent: 'center' }}>
      <div style={{
        maxWidth: 560, borderLeft: '4px solid #c0392b', background: 'var(--card, #fff)',
        borderRadius: 8, padding: '20px 24px', boxShadow: '0 1px 3px rgba(0,0,0,.12)',
      }}>
        <h2 style={{ margin: '0 0 8px', fontSize: 18 }}>Geen toegang tot Rhadix Datastation</h2>
        <p style={{ margin: '0 0 16px', lineHeight: 1.5 }}>{melding}</p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => { window.location.href = platformUrl() }}
                  title="Terug naar het Platform — kies een applicatie">
            ▦ Terug naar Platform
          </button>
          <button onClick={onLogout}>Uitloggen</button>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const [authUser, setAuthUser] = useState(null)
  const [booting, setBooting]   = useState(true)
  const [geenToegang, setGeenToegang] = useState(null)

  useEffect(() => {
    const onUnauth = () => setAuthUser(null)
    window.addEventListener('rhadix:unauthorized', onUnauth)
    return () => window.removeEventListener('rhadix:unauthorized', onUnauth)
  }, [])

  useEffect(() => {
    const onGeenToegang = (e) => setGeenToegang(e.detail)
    window.addEventListener('rhadix:geen-app-toegang', onGeenToegang)
    return () => window.removeEventListener('rhadix:geen-app-toegang', onGeenToegang)
  }, [])

  // SSO-bootstrap: probeer bij het laden automatisch in te loggen via het
  // centrale rhadix_sso-cookie (same-origin -> cookie gaat mee). Geen sessie -> loginscherm.
  useEffect(() => {
    let alive = true
    getMe()
      .then(me => { if (alive) { applyBranding(me.branding); setAuthUser({ ...me, name: me.full_name || me.email }) } })
      .catch(() => {})
      .finally(() => { if (alive) setBooting(false) })
    return () => { alive = false }
  }, [])

  async function handleLogin(email, password) {
    await apiLogin(email, password)
    const me = await getMe()
    applyBranding(me.branding)
    setAuthUser({ ...me, name: me.full_name || me.email })
  }
  function handleLogout() { clearAuthToken(); setAuthUser(null); setGeenToegang(null) }

  if (booting) return (<><EnvBanner /><div style={{ padding: 48, textAlign: 'center', color: 'var(--text3)' }}>Bezig met inloggen…</div></>)
  if (!authUser) return (<><EnvBanner /><LoginScreen onLogin={handleLogin} /></>)
  if (geenToegang) return (<><EnvBanner /><GeenAppToegang melding={geenToegang} onLogout={handleLogout} /></>)

  const isPlatform = authUser.role === 'PLATFORM_ADMIN'
  const isAdmin    = isPlatform || authUser.role === 'ORG_ADMIN'

  const navLinks = [
    { to: '/datastation', label: 'Datastation' },
    ...(isAdmin    ? [{ to: '/gebruikers',   label: 'Gebruikers' }] : []),
    ...(isPlatform ? [{ to: '/organisaties', label: 'Organisaties' }] : []),
  ]

  return (
    <>
      <EnvBanner />
      <Nav authUser={authUser} onLogout={handleLogout} links={navLinks} />
      <Routes>
        <Route path="/" element={<Home authUser={authUser} />} />
        <Route path="/datastation" element={<Datastation />} />
        <Route path="/gebruikers" element={isAdmin ? <Gebruikersbeheer authUser={authUser} /> : <Navigate to="/" replace />} />
        <Route path="/organisaties" element={isPlatform ? <Organisaties /> : <Navigate to="/" replace />} />
        <Route path="/404" element={<NotFound />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </>
  )
}
