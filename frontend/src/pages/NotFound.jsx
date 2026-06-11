import { Link } from 'react-router-dom'
import { Page, PageTitle } from '../components/UI'
export default function NotFound() {
  return (
    <Page>
      <PageTitle title="404 — Niet gevonden" sub="Deze pagina bestaat niet." />
      <Link to="/" style={{ color: 'var(--blue)', fontWeight: 600 }}>← Terug naar start</Link>
    </Page>
  )
}
