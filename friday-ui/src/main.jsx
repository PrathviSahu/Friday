import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { registerPresenceWorker, subscribePresencePush } from './services/presencePush.js'

// Phase 2.5 — Cross-Device Presence: wake-on-push approvals via service worker.
// No permission prompt on load; subscribe only when permission was already granted.
registerPresenceWorker().then(() => subscribePresencePush());

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
