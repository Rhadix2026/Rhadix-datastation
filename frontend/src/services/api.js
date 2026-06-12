const BASE = '/api'

let _token = null
export function setAuthToken(t) { _token = t }
export function getAuthToken()  { return _token }
export function clearAuthToken(){ _token = null }

function authHeaders(extra = {}) {
  return _token ? { Authorization: `Bearer ${_token}`, ...extra } : { ...extra }
}

async function req(method, path, body) {
  const opts = { method, headers: authHeaders(body ? { 'Content-Type': 'application/json' } : {}) }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const res = await fetch(`${BASE}${path}`, opts)
  if (res.status === 401) { clearAuthToken(); window.dispatchEvent(new CustomEvent('rhadix:unauthorized')) }
  if (!res.ok) {
    let detail = `Fout ${res.status}`
    try { const j = await res.json(); detail = j.detail || detail } catch {}
    throw new Error(detail)
  }
  return res.status === 204 ? null : res.json()
}

// ── Meta ──
export const getMeta   = () => req('GET', '/meta')
export const getHealth = () => req('GET', '/health')

// ── Auth ──
export async function login(email, password) {
  const data = await req('POST', '/auth/login', { email, password })
  setAuthToken(data.access_token)
  return data
}
export const getMe          = () => req('GET', '/auth/me')
export const changePassword = (current_password, new_password) =>
  req('PATCH', '/auth/me/password', { current_password, new_password })

// ── Platform-admin: organisaties ──
export const listTenants     = () => req('GET', '/admin/tenants')
export const createTenant    = (b) => req('POST', '/admin/tenants', b)
export const listTenantUsers = (tenantId) => req('GET', `/admin/tenants/${tenantId}/users`)
export const platformStats   = () => req('GET', '/admin/stats')

// ── Org-admin: gebruikers binnen eigen organisatie ──
export const listOrgUsers   = () => req('GET', '/org/users')
export const createOrgUser  = (b) => req('POST', '/org/users', b)
export const toggleUser     = (id) => req('PATCH', `/org/users/${id}/deactivate`)
export const resetUserPwd   = (id, new_password) => req('POST', `/org/users/${id}/reset-password`, { new_password })
export const deleteOrgUser  = (id) => req('DELETE', `/org/users/${id}`)

// ── Uitwisselprofielen ──
export const listProfielen = () => req('GET', '/profielen')
export const getProfiel    = (key) => req('GET', `/profielen/${key}`)

// ── Zorgaanbieders ──
export const listZorgaanbieders   = () => req('GET', '/zorgaanbieders')
export const registerZorgaanbieder = (b) => req('POST', '/zorgaanbieders/register', b)

// ── Uitvragen ──
export const createUitvraag = (b) => req('POST', '/uitvragen', b)
export const listUitvragen  = () => req('GET', '/uitvragen')
export const getUitvraag    = (id) => req('GET', `/uitvragen/${id}`)

// Export-download met auth-header → blob → bestand opslaan
export async function downloadUitvraag(id, fmt = 'csv') {
  const res = await fetch(`${BASE}/uitvragen/${id}/export.${fmt}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Export mislukt (${res.status})`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `uitvraag-${id.slice(0, 8)}.${fmt}`
  document.body.appendChild(a); a.click(); a.remove()
  URL.revokeObjectURL(url)
}

// ── Analyse / Monitor ──
export const getUitvraagStats = () => req('GET', '/uitvragen/stats')

// ── Capabilities (geïmplementeerde uitwisselprofielen) ──
export const getCapabilitiesOverzicht = () => req('GET', '/capabilities/overzicht')
export const getAanbiedersVoorProfiel = (key, inclusiefNietProductie = false) =>
  req('GET', `/capabilities/profiel/${key}?inclusief_niet_productie=${inclusiefNietProductie}`)

export async function importCapabilities(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${BASE}/capabilities/import`, { method: 'POST', headers: authHeaders(), body: fd })
  if (res.status === 401) { clearAuthToken(); window.dispatchEvent(new CustomEvent('rhadix:unauthorized')) }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Import mislukt (${res.status})`)
  return data
}

// ── Datastation ──
export const dsStatus      = () => req('GET', '/datastation/status')
export const dsRules       = () => req('GET', '/datastation/rules')
export const dsLaadTestset = () => req('POST', '/datastation/laad-testset')
export const dsReset       = () => req('POST', '/datastation/reset')
export const dsBeantwoord  = (sparql) => req('POST', '/datastation/beantwoord', { sparql })
export const dsLaadHappyflow     = () => req('POST', '/datastation/laad-happyflow')
export const dsHappyflowOverzicht = () => req('GET', '/datastation/happyflow-overzicht')
// ── Vraag-inbox ──
export const dsVraagIndienen = (b) => req('POST', '/datastation/vragen', b)
export const dsVragen        = (status = 'open') => req('GET', `/datastation/vragen?status=${status}`)
export const dsVraagStats    = () => req('GET', '/datastation/vragen/stats')
export const dsVraagDetail   = (id) => req('GET', `/datastation/vragen/${id}`)
export const dsAccordeer     = (id) => req('POST', `/datastation/vragen/${id}/accordeer`)
export const dsOverschrijf   = (id, waarde, toelichting) => req('POST', `/datastation/vragen/${id}/overschrijf`, { waarde, toelichting })
export const dsAfwijzen      = (id, reden) => req('POST', `/datastation/vragen/${id}/wijs-af`, { reden })
export const dsAccordeerAlles = () => req('POST', '/datastation/vragen/accordeer-alles')
export const dsResultaat     = (id) => req('GET', `/datastation/vragen/${id}/resultaat`)

export async function dsUpload(file, mappingJson, classUri) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('mapping', mappingJson)
  if (classUri) fd.append('class_uri', classUri)
  const res = await fetch(`${BASE}/datastation/upload`, { method: 'POST', headers: authHeaders(), body: fd })
  const d = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(d.detail || `Upload mislukt (${res.status})`)
  return d
}
