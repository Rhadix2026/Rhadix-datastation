// ─── Merk-laag (white-label) ─ default Rhadix; 'suresync' alleen op staging ───
// SureSync-kleuren uit officieel logo: violet #7344F3 + navy #101948.
export const BRANDS = {
  rhadix:   { name: 'Rhadix',   logo: '/rhadix-logo.jpg' },
  kikv:     { name: 'KIK-V',    logo: '/kikv-logo.png' },
}
export function currentBrand() {
  try { return document.documentElement.dataset.brand || 'rhadix' } catch { return 'rhadix' }
}
let _tenantLogo = null
export function brandLogo() {
  if (_tenantLogo) return _tenantLogo
  const b = BRANDS[currentBrand()] || BRANDS.rhadix
  return b.logo
}
export function applyInitialBrand() {
  // Alt-skins (suresync/kikv) alleen buiten productie; productie blijft Rhadix.
  const isProd = (import.meta?.env?.VITE_RHADIX_ENV === 'production')
  const allowed = isProd ? ['rhadix'] : ['rhadix', 'kikv']
  let key = 'rhadix'
  try {
    // Navy (Rhadix) is standaard; KIK-V alleen via expliciete ?brand=kikv (demo), blijft niet plakken.
    const p = new URLSearchParams(window.location.search).get('brand')
    if (allowed.includes(p)) key = p
    document.documentElement.dataset.brand = key
  } catch { /* ignore */ }
}
export function toggleBrand() {
  const next = currentBrand() === 'kikv' ? 'rhadix' : 'kikv'
  try {
    sessionStorage.setItem('rhadix:brand', next)
    const u = new URL(window.location.href); u.searchParams.set('brand', next)
    window.location.href = u.toString()
  } catch { /* ignore */ }
}

// ─── Tenant-branding uit het centrale SSO-token (kleuren + logo) ─────────────
function _hexToRgb(hex) {
  if (!hex) return null
  let h = String(hex).replace('#', '')
  if (h.length === 3) h = h.split('').map(c => c + c).join('')
  if (h.length !== 6) return null
  const n = parseInt(h, 16)
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }
}
function _toHex({ r, g, b }) {
  const c = v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')
  return `#${c(r)}${c(g)}${c(b)}`
}
function _mix(hex, target, amount) {
  const a = _hexToRgb(hex), b = _hexToRgb(target)
  if (!a || !b) return hex
  return _toHex({ r: a.r + (b.r - a.r) * amount, g: a.g + (b.g - a.g) * amount, b: a.b + (b.b - a.b) * amount })
}

// Pas de effectieve tenant-branding toe: onthoud het logo (brandLogo() geeft het
// voortaan terug) en zet de kleur-CSS-variabelen op <html>. Veilig bij null.
export function applyBranding(branding) {
  if (!branding) return
  if (branding.logo_url) _tenantLogo = branding.logo_url
  const primary = branding.primary_color
  const accent  = branding.accent_color || primary
  if (!primary) return
  const root = document.documentElement
  const dark  = _mix(primary, '#000000', 0.18)
  const light = _mix(primary, '#ffffff', 0.90)
  const midc  = _mix(primary, '#ffffff', 0.55)
  const set = (k, v) => root.style.setProperty(k, v)
  set('--blue', primary); set('--blue-dark', dark); set('--blue-hero', accent)
  set('--blue-light', light); set('--blue-mid', midc); set('--accent', accent)
  set('--k-blue', primary); set('--k-blue-strong', dark)
  set('--k-blue-light', light); set('--k-blue-mid', midc)
}
