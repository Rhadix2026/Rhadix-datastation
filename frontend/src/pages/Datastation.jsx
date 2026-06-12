import { useEffect, useState, Fragment } from 'react'
import { Page, PageTitle, Card, BtnPrimary, BtnGhost } from '../components/UI'
import { dsStatus, dsRules, dsLaadTestset, dsReset, dsBeantwoord, dsUpload, dsLaadHappyflow, dsHappyflowOverzicht,
  dsVragen, dsVraagStats, dsVraagIndienen, dsAccordeer, dsOverschrijf, dsAfwijzen, dsAccordeerAlles } from '../services/api'

const DEMO_SPARQL = `PREFIX onz-pers: <http://purl.org/ozo/onz-pers#>
SELECT (COUNT(?m) AS ?n) WHERE {
  ?m a onz-pers:Medewerker .
}`

function Stat({ label, value }) {
  return (
    <Card style={{ display: 'flex', flexDirection: 'column', gap: 2, minHeight: 76 }}>
      <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.5px' }}>{label}</span>
      <span style={{ fontSize: 26, fontWeight: 800, color: 'var(--text)' }}>{value}</span>
    </Card>
  )
}

export default function Datastation() {
  const [status, setStatus] = useState(null)
  const [rules, setRules]   = useState(null)
  const [sparql, setSparql] = useState(DEMO_SPARQL)
  const [antwoord, setAntwoord] = useState(null)
  const [bezig, setBezig]   = useState(false)
  const [fout, setFout]     = useState(null)
  const [upFile, setUpFile] = useState(null)
  const [upMapping, setUpMapping] = useState('{\n  "kolomnaam": {"concept_uri": "http://purl.org/ozo/onz-pers#functie", "kind": "data", "datatype": "string"}\n}')
  const [upClass, setUpClass] = useState('http://purl.org/ozo/onz-pers#Medewerker')
  const [upRes, setUpRes] = useState(null)
  const [hf, setHf] = useState(null)
  const [inbox, setInbox] = useState([])
  const [verzonden, setVerzonden] = useState([])
  const [vstats, setVstats] = useState(null)
  const [ovId, setOvId] = useState(null)
  const [ovWaarde, setOvWaarde] = useState('')
  const [ovReden, setOvReden] = useState('')
  const [hfBezig, setHfBezig] = useState(false)

  function ververs() {
    dsStatus().then(setStatus).catch(e => setFout(e.message))
    dsRules().then(setRules).catch(() => {})
  }
  function verversHf() { dsHappyflowOverzicht().then(setHf).catch(() => {}) }
  function verversInbox() {
    dsVragen('open').then(d => setInbox(d.vragen)).catch(() => {})
    dsVragen('verzonden').then(d => setVerzonden(d.vragen)).catch(() => {})
    dsVraagStats().then(setVstats).catch(() => {})
  }
  useEffect(() => { ververs(); verversHf(); verversInbox() }, [])

  const TESTVRAAG = 'PREFIX kik: <https://kik-v.nl/ns#>\nSELECT (AVG(?w) AS ?waarde) WHERE { ?o a kik:Observatie ; kik:indicator "2.1" ; kik:waarde ?w }'
  async function stuurTestvraag() {
    setBezig(true); setFout(null)
    try { await dsVraagIndienen({ sparql: TESTVRAAG, afnemer: 'Rhadix Uitvraag (test)', indicator_code: '2.1' }); verversInbox() }
    catch (e) { setFout(e.message) } finally { setBezig(false) }
  }
  async function accorderen(id) {
    setBezig(true); setFout(null)
    try { await dsAccordeer(id); verversInbox() } catch (e) { setFout(e.message) } finally { setBezig(false) }
  }
  async function accorderenAlles() {
    setBezig(true); setFout(null)
    try { await dsAccordeerAlles(); verversInbox() } catch (e) { setFout(e.message) } finally { setBezig(false) }
  }
  function startOverschrijf(v) { setOvId(v.query_id); setOvWaarde(v.berekende_waarde ?? ''); setOvReden('') }
  async function bevestigOverschrijf() {
    setBezig(true); setFout(null)
    try { await dsOverschrijf(ovId, parseFloat(ovWaarde), ovReden); setOvId(null); verversInbox() }
    catch (e) { setFout(e.message) } finally { setBezig(false) }
  }
  async function afwijzen(id) {
    const reden = window.prompt('Reden van afwijzing (optioneel):') ?? null
    setBezig(true); setFout(null)
    try { await dsAfwijzen(id, reden); verversInbox() } catch (e) { setFout(e.message) } finally { setBezig(false) }
  }

  async function laadHappyflow() {
    setHfBezig(true); setFout(null)
    try { await dsLaadHappyflow(); ververs(); verversHf() }
    catch (e) { setFout(e.message) } finally { setHfBezig(false) }
  }
  async function laden() {
    setBezig(true); setFout(null)
    try { await dsLaadTestset(); ververs() } catch (e) { setFout(e.message) } finally { setBezig(false) }
  }
  async function leeg() {
    setBezig(true); try { await dsReset(); setAntwoord(null); ververs() } finally { setBezig(false) }
  }
  async function beantwoord() {
    setBezig(true); setFout(null); setAntwoord(null)
    try { setAntwoord(await dsBeantwoord(sparql)) } catch (e) { setFout(e.message) } finally { setBezig(false) }
  }

  async function uploaden() {
    if (!upFile) { setFout('Kies eerst een CSV-bestand.'); return }
    setBezig(true); setFout(null); setUpRes(null)
    try { setUpRes(await dsUpload(upFile, upMapping, upClass)); ververs() }
    catch (e) { setFout(e.message) } finally { setBezig(false) }
  }

  const datasets = status ? Object.entries(status.datasets) : []

  return (
    <Page>
      <PageTitle badge="Datastation" title="🗄️ Rhadix Datastation"
        sub="Brondata wordt lokaal afgebeeld op KIK-V-concepten (RDF) en gevalideerde vragen worden hier berekend. De data blijft bij de bron; alleen het antwoord reist." />

      {fout && <Card style={{ marginBottom: 16, background: 'var(--red-light)', border: '1px solid var(--red)' }}><span style={{ color: 'var(--red)' }}>{fout}</span></Card>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 18 }}>
        <Stat label="Triple store" value={status?.fuseki ? 'Fuseki' : 'rdflib'} />
        <Stat label="Datasets" value={status ? Object.keys(status.datasets).length : '—'} />
        <Stat label="RDF-triples" value={status ? status.triples : '—'} />
        <Stat label="Happy-flow regels" value={rules ? rules.aantal : '—'} />
      </div>

      <Card style={{ marginBottom: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ maxWidth: 560 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>📥 Vraag-inbox</div>
            <div style={{ fontSize: 13, color: 'var(--text3)' }}>Binnengekomen gevalideerde vragen. Het datastation berekent een voorstel-antwoord; de zorgaanbieder <b>accordeert</b>, <b>overschrijft</b> handmatig of <b>wijst af</b>. Pas na verzending haalt de afnemer het resultaat op.</div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <BtnGhost onClick={stuurTestvraag} disabled={bezig}>Stuur testvraag</BtnGhost>
            {inbox.some(v => v.status === 'TE_BEOORDELEN') && <BtnPrimary onClick={accorderenAlles} disabled={bezig}>✓ Alles accorderen</BtnPrimary>}
            <BtnGhost onClick={verversInbox} disabled={bezig}>Ververs</BtnGhost>
          </div>
        </div>
        {vstats && (
          <div style={{ display: 'flex', gap: 18, marginTop: 12, fontSize: 13 }}>
            <span>Te beoordelen: <b style={{ color: 'var(--amber)' }}>{vstats.te_beoordelen}</b></span>
            <span>Verzonden: <b style={{ color: 'var(--green)' }}>{vstats.verzonden}</b></span>
            <span>Afgewezen: <b style={{ color: 'var(--text2)' }}>{vstats.afgewezen}</b></span>
            <span>Fout: <b style={{ color: 'var(--red)' }}>{vstats.fout}</b></span>
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 6 }}>Te beoordelen</div>
          {inbox.length === 0 && <div style={{ fontSize: 13, color: 'var(--text3)' }}>Geen openstaande vragen. Klik op “Stuur testvraag”.</div>}
          {inbox.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr style={{ color: 'var(--text3)', textAlign: 'left' }}>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Afnemer</th>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Indicator</th>
                <th style={{ padding: '4px 8px', fontWeight: 600, textAlign: 'right' }}>Berekend</th>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '4px 8px', fontWeight: 600, textAlign: 'right' }}>Acties</th>
              </tr></thead>
              <tbody>
                {inbox.map(v => (
                  <Fragment key={v.query_id}>
                    <tr style={{ borderTop: '1px solid var(--border)' }}>
                      <td style={{ padding: '6px 8px', color: 'var(--text)' }}>{v.afnemer || '—'}</td>
                      <td style={{ padding: '6px 8px', color: 'var(--text3)' }}>{v.indicator_code || '—'}</td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700 }}>{v.berekende_waarde ?? '—'}</td>
                      <td style={{ padding: '6px 8px' }}><span style={{ color: v.status === 'FOUT' ? 'var(--red)' : 'var(--amber)', fontWeight: 600 }}>{v.status}</span></td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {v.status === 'TE_BEOORDELEN' && <button onClick={() => accorderen(v.query_id)} disabled={bezig} style={{ marginRight: 6, padding: '3px 10px', borderRadius: 6, border: 'none', background: 'var(--green)', color: '#fff', fontWeight: 600, cursor: 'pointer', fontSize: 12 }}>Accorderen</button>}
                        <button onClick={() => startOverschrijf(v)} disabled={bezig} style={{ marginRight: 6, padding: '3px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer', fontSize: 12 }}>Overschrijven</button>
                        <button onClick={() => afwijzen(v.query_id)} disabled={bezig} style={{ padding: '3px 10px', borderRadius: 6, border: '1px solid var(--border)', background: 'transparent', color: 'var(--red)', cursor: 'pointer', fontSize: 12 }}>Afwijzen</button>
                      </td>
                    </tr>
                    {ovId === v.query_id && (
                      <tr style={{ background: 'var(--bg2, #f7f9fc)' }}>
                        <td colSpan={5} style={{ padding: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: 12, color: 'var(--text2)' }}>Handmatige waarde:</span>
                            <input type="number" value={ovWaarde} onChange={e => setOvWaarde(e.target.value)} style={{ width: 110, padding: '4px 8px', borderRadius: 6, border: '1.5px solid var(--border)', fontSize: 13 }} />
                            <input placeholder="reden / toelichting" value={ovReden} onChange={e => setOvReden(e.target.value)} style={{ flex: 1, minWidth: 180, padding: '4px 8px', borderRadius: 6, border: '1.5px solid var(--border)', fontSize: 13 }} />
                            <BtnPrimary onClick={bevestigOverschrijf} disabled={bezig || ovWaarde === ''}>Verzenden</BtnPrimary>
                            <BtnGhost onClick={() => setOvId(null)}>Annuleer</BtnGhost>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
        {verzonden.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '.5px', marginBottom: 6 }}>Verzonden</div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr style={{ color: 'var(--text3)', textAlign: 'left' }}>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Afnemer</th>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Indicator</th>
                <th style={{ padding: '4px 8px', fontWeight: 600, textAlign: 'right' }}>Definitief</th>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Wijze</th>
                <th style={{ padding: '4px 8px', fontWeight: 600 }}>Beoordeeld door</th>
              </tr></thead>
              <tbody>
                {verzonden.map(v => (
                  <tr key={v.query_id} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '6px 8px', color: 'var(--text)' }}>{v.afnemer || '—'}</td>
                    <td style={{ padding: '6px 8px', color: 'var(--text3)' }}>{v.indicator_code || '—'}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700 }}>{v.definitieve_waarde ?? '—'}</td>
                    <td style={{ padding: '6px 8px' }}>{v.handmatig ? <span style={{ color: 'var(--amber)', fontWeight: 600 }}>handmatig</span> : <span style={{ color: 'var(--green)', fontWeight: 600 }}>geaccordeerd</span>}</td>
                    <td style={{ padding: '6px 8px', color: 'var(--text3)' }}>{v.beoordeeld_door || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card style={{ marginBottom: 18, border: '1.5px solid var(--brand, #2563eb)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ maxWidth: 560 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text)' }}>Happy-flow testset</div>
            <div style={{ fontSize: 13, color: 'var(--text3)' }}>De volledige ingebouwde happy-flow van de digital twin: één fictieve zorgaanbieder over alle referentieontwerpen (cliënten, medewerkers, vestigingen, financieel, AFAS Profit). Per indicator vergelijken we de <b>validatie-berekening</b> op de brondata met het <b>datastation-antwoord</b> via SPARQL op de RDF-store.</div>
          </div>
          <BtnPrimary onClick={laadHappyflow} disabled={hfBezig}>{hfBezig ? 'Bezig…' : 'Laad happy-flow testset'}</BtnPrimary>
        </div>
        {hf && (
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, color: hf.geladen ? 'var(--green)' : 'var(--text3)', fontWeight: 600, marginBottom: 10 }}>
              {hf.geladen ? `✓ ${hf.match}/${hf.aantal} indicatoren kloppen — validatie == datastation` : `${hf.aantal} indicatoren · nog niet ingeladen (klik 'Laad happy-flow testset')`}
            </div>
            {Object.entries(hf.per_dataset).map(([ds, items]) => (
              <div key={ds} style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text2)', fontFamily: 'monospace', marginBottom: 4 }}>{ds}</div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead><tr style={{ color: 'var(--text3)', textAlign: 'left' }}>
                    <th style={{ padding: '3px 8px', fontWeight: 600 }}>Indicator</th>
                    <th style={{ padding: '3px 8px', fontWeight: 600 }}>Aggregatie</th>
                    <th style={{ padding: '3px 8px', fontWeight: 600, textAlign: 'right' }}>Validatie</th>
                    <th style={{ padding: '3px 8px', fontWeight: 600, textAlign: 'right' }}>Datastation</th>
                    <th style={{ padding: '3px 8px', fontWeight: 600, textAlign: 'center' }}></th>
                  </tr></thead>
                  <tbody>
                    {items.map(i => (
                      <tr key={i.indicator_id} style={{ borderTop: '1px solid var(--border)' }}>
                        <td style={{ padding: '4px 8px', color: 'var(--text)' }}>{i.name}</td>
                        <td style={{ padding: '4px 8px', color: 'var(--text3)', fontFamily: 'monospace', fontSize: 12 }}>{i.aggregatie}</td>
                        <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>{i.validatie ?? '—'}</td>
                        <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600 }}>{i.datastation ?? '—'}</td>
                        <td style={{ padding: '4px 8px', textAlign: 'center' }}>{i.match ? <span style={{ color: 'var(--green)' }}>✓</span> : (hf.geladen ? <span style={{ color: 'var(--red)' }}>✗</span> : '')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card style={{ marginBottom: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Testset (happy-flow)</div>
            <div style={{ fontSize: 13, color: 'var(--text3)' }}>Laad de demo-brondata in: afbeelden naar concepten → RDF in de store.</div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <BtnGhost onClick={leeg} disabled={bezig}>Leegmaken</BtnGhost>
            <BtnPrimary onClick={laden} disabled={bezig}>{bezig ? 'Bezig…' : 'Laad testset'}</BtnPrimary>
          </div>
        </div>
        {datasets.length > 0 && (
          <div style={{ marginTop: 12, fontSize: 13, color: 'var(--text2)' }}>
            Ingeladen: {datasets.map(([n, c]) => <span key={n} style={{ marginRight: 12 }}>{n} <b>({c})</b></span>)}
          </div>
        )}
      </Card>

      <Card style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>Echte brondata inladen</div>
        <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 12 }}>Upload een CSV (bv. een happy-flow bronbestand) met een kolom→concept-mapping; het datastation beeldt het af op RDF.</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input type="file" accept=".csv,text/csv" onChange={e => setUpFile(e.target.files?.[0] || null)} style={{ fontSize: 13 }} />
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>RDF-class (rdf:type per record)</label>
          <input value={upClass} onChange={e => setUpClass(e.target.value)} style={{ padding: '8px 12px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'monospace' }} />
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text2)' }}>Mapping (JSON: kolom → concept)</label>
          <textarea value={upMapping} onChange={e => setUpMapping(e.target.value)} rows={5} style={{ fontFamily: 'monospace', fontSize: 12, padding: '10px 12px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', resize: 'vertical' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <BtnPrimary onClick={uploaden} disabled={bezig}>Inladen</BtnPrimary>
            {upRes && <span style={{ fontSize: 13, color: 'var(--green)' }}>✓ {upRes.dataset}: {upRes.records} records → {upRes.triples} triples</span>}
          </div>
        </div>
      </Card>

      <Card style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>Gevalideerde vraag beantwoorden</div>
        <div style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 12 }}>Voer een SPARQL-vraag uit op de ingeladen store (zoals Uitvraag dat straks doet).</div>
        <textarea value={sparql} onChange={e => setSparql(e.target.value)} rows={6}
          style={{ width: '100%', fontFamily: 'monospace', fontSize: 13, padding: '12px 14px', borderRadius: 'var(--radius)', border: '1.5px solid var(--border)', background: '#0f1a30', color: '#cfe2f3', outline: 'none', resize: 'vertical' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 12 }}>
          <BtnPrimary onClick={beantwoord} disabled={bezig}>Beantwoord</BtnPrimary>
          {antwoord && (
            <span style={{ fontSize: 14 }}>
              <b style={{ color: antwoord.status === 'OK' ? 'var(--green)' : 'var(--amber)' }}>{antwoord.status}</b>
              {antwoord.waarde != null && <> · waarde: <b>{antwoord.waarde}</b></>}
              <span style={{ color: 'var(--text3)' }}> · {antwoord.backend}</span>
              {antwoord.toelichting && <span style={{ color: 'var(--text3)' }}> · {antwoord.toelichting}</span>}
            </span>
          )}
        </div>
      </Card>

      {rules && (
        <Card style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px 6px', fontSize: 13, fontWeight: 700, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '.5px' }}>Happy-flow regels per dataset</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <tbody>
              {Object.entries(rules.per_dataset).map(([ds, items]) => (
                <tr key={ds} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '10px 20px', fontWeight: 600, color: 'var(--text)', width: '32%', verticalAlign: 'top' }}>{ds}</td>
                  <td style={{ padding: '10px 20px', color: 'var(--text3)' }}>{items.map(i => i.name).join(' · ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </Page>
  )
}
