// ─── Merk-laag (white-label) ─ default Rhadix; 'suresync' alleen op staging ───
// SureSync-kleuren uit officieel logo: violet #7344F3 + navy #101948.
export const BRANDS = {
  rhadix:   { name: 'Rhadix',   logo: '/rhadix-logo.jpg' },
  kikv:     { name: 'KIK-V',    logo: '/kikv-logo.png' },
}
export function currentBrand() {
  try { return document.documentElement.dataset.brand || 'rhadix' } catch { return 'rhadix' }
}
export function brandLogo() {
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
