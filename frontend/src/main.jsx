import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
import { applyInitialBrand } from './brand'

applyInitialBrand()

// Browser-terug na uitloggen mag geen ingelogd scherm meer tonen. Een pagina die
// de browser uit zijn back/forward-cache haalt wordt niet opnieuw opgebouwd: de
// SSO-bootstrap wordt dan overgeslagen en het oude scherm komt terug zoals het
// was. Opnieuw laden dwingt die sessiecontrole af.
window.addEventListener('pageshow', (e) => { if (e.persisted) window.location.reload() })

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
