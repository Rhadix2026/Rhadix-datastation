import { brandLogo, currentBrand } from '../brand'
// ─── Rhadix Uitvraag wordmerk (eigen SVG, in de Rhadix-huisstijl) ────────────
// Eigen merk binnen de Rhadix-familie: zelfde look & feel (navy + accentblauw,
// Oxanium), maar herkenbaar als de uitvraag-app voor ketenpartijen.

export function UitvraagMark({ size = 34 }) {
  // Gestileerde knopen + verbindingen → het federatieve KIK-V-netwerk
  // (decentrale datastations rond de afnemer die de vraag stelt).
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <circle cx="20" cy="20" r="19" fill="var(--blue-hero)" />
      <line x1="20" y1="20" x2="11" y2="12" stroke="var(--accent)" strokeWidth="1.6" />
      <line x1="20" y1="20" x2="30" y2="13" stroke="var(--accent)" strokeWidth="1.6" />
      <line x1="20" y1="20" x2="13" y2="29" stroke="var(--accent)" strokeWidth="1.6" />
      <line x1="20" y1="20" x2="29" y2="28" stroke="var(--accent)" strokeWidth="1.6" />
      <circle cx="20" cy="20" r="4.2" fill="#fff" />
      <circle cx="11" cy="12" r="2.6" fill="var(--accent)" />
      <circle cx="30" cy="13" r="2.6" fill="var(--accent)" />
      <circle cx="13" cy="29" r="2.6" fill="var(--blue-mid)" />
      <circle cx="29" cy="28" r="2.6" fill="var(--blue-mid)" />
    </svg>
  )
}

export function UitvraagLogo({ size = 34, color = '#fff', onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'none', border: 'none', cursor: onClick ? 'pointer' : 'default', padding: 0,
      }}
    >
      {<>
            <UitvraagMark size={size} />
            <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', lineHeight: 1 }}>
              <span style={{ fontWeight: 800, fontSize: 18, color, letterSpacing: '-0.01em' }}>
                Rhadix<span style={{ color: 'var(--accent)' }}> </span>Datastation
              </span>
              <span style={{ fontSize: 9.5, fontWeight: 600, color: 'var(--accent)', letterSpacing: '2px', textTransform: 'uppercase' }}>
                KIK-V
              </span>
            </span>
          </>}
    </button>
  )
}
