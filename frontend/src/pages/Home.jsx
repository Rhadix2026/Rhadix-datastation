import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Page, PageTitle, Card, StatusDot } from '../components/UI'
import { getMeta, getHealth } from '../services/api'

export default function Home({ authUser }) {
  const navigate = useNavigate()
  const [meta, setMeta] = useState(null)
  const [backendOk, setBackendOk] = useState(null)

  useEffect(() => {
    getHealth().then(() => setBackendOk(true)).catch(() => setBackendOk(false))
    getMeta().then(setMeta).catch(() => {})
  }, [])

  const isPlatform = authUser?.role === 'PLATFORM_ADMIN'
  const isAdmin    = isPlatform || authUser?.role === 'ORG_ADMIN'

  const cards = [
    { to: '/datastation', icon: '🗄️', title: 'Datastation', desc: 'Brondata afbeelden op KIK-V-concepten (RDF) en gevalideerde vragen lokaal berekenen.', status: 'Beschikbaar' },
    ...(isAdmin ? [{ to: '/gebruikers', icon: '👥', title: 'Gebruikersbeheer', desc: 'Gebruikers in uw organisatie beheren: rollen, (de)activeren, wachtwoorden.', status: 'Beschikbaar' }] : []),
    ...(isPlatform ? [{ to: '/organisaties', icon: '🏢', title: 'Organisaties', desc: 'Organisaties op het platform beheren en beheerders aanmaken.', status: 'Beschikbaar' }] : []),
  ]

  return (
    <Page>
      <PageTitle badge={`Ingelogd als ${authUser?.name || authUser?.email}`}
        title="Welkom bij Rhadix Datastation"
        sub="Het federatieve KIK-V-datastation: brondata wordt lokaal op concepten afgebeeld en gevalideerde vragen worden hier berekend." />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20, marginBottom: 28 }}>
        {cards.map(m => (
          <Card key={m.to} onClick={() => navigate(m.to)} style={{ display: 'flex', flexDirection: 'column', gap: 10, minHeight: 150 }}>
            <div style={{ fontSize: 28 }}>{m.icon}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>{m.title}</div>
            <div style={{ fontSize: 13, color: 'var(--text3)', lineHeight: 1.5, flex: 1 }}>{m.desc}</div>
            <span style={{ alignSelf: 'flex-start', fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 99, color: 'var(--green)', background: 'var(--green-light)' }}>{m.status}</span>
          </Card>
        ))}
      </div>

      <Card style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
        <StatusDot ok={backendOk} label={backendOk == null ? 'Backend controleren…' : backendOk ? 'Backend verbonden' : 'Backend onbereikbaar'} />
        {meta && <span style={{ fontSize: 12, color: 'var(--text3)' }}>{meta.app || 'Rhadix Datastation'} · versie {meta.version} · omgeving: {meta.environment}</span>}
      </Card>
    </Page>
  )
}
