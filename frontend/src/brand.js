// ─── Merk-laag (white-label) ─ default Rhadix; 'suresync' alleen op staging ───
// SureSync-kleuren uit officieel logo: violet #7344F3 + navy #101948.
export const BRANDS = {
  rhadix:   { name: 'Rhadix',   logo: '/rhadix-logo.jpg' },
  suresync: { name: 'SureSync', logo: '/suresync-logo-light.svg' },
}
export function currentBrand() {
  try { return document.documentElement.dataset.brand || 'rhadix' } catch { return 'rhadix' }
}
export function brandLogo() {
  const b = BRANDS[currentBrand()] || BRANDS.rhadix
  return b.logo
}
export function applyInitialBrand() {
  let key = 'rhadix'
  try {
    const p = new URLSearchParams(window.location.search).get('brand')
    if (p === 'suresync' || p === 'rhadix') key = p
    else {
      const s = sessionStorage.getItem('rhadix:brand')
      if (s === 'suresync' || s === 'rhadix') key = s
    }
    sessionStorage.setItem('rhadix:brand', key)
    document.documentElement.dataset.brand = key
  } catch { /* ignore */ }
}
export function toggleBrand() {
  const next = currentBrand() === 'suresync' ? 'rhadix' : 'suresync'
  try {
    sessionStorage.setItem('rhadix:brand', next)
    const u = new URL(window.location.href); u.searchParams.set('brand', next)
    window.location.href = u.toString()
  } catch { /* ignore */ }
}
