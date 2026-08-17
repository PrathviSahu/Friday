import { Component, StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { registerPresenceWorker, subscribePresencePush } from './services/presencePush.js'

class RootErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('[RootErrorBoundary] Caught fatal error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          height: '100vh', width: '100vw', background: '#010817', color: '#DFFAFF',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'Orbitron, sans-serif', padding: 24, textAlign: 'center'
        }}>
          <div style={{ fontSize: 24, fontWeight: 700, color: '#00B7FF', marginBottom: 12 }}>
            F.R.I.D.A.Y. CORE RECOVERY
          </div>
          <div style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: 13, color: '#94a3b8', maxWidth: 460, marginBottom: 20 }}>
            {this.state.error?.message || 'A minor subsystem encountered an unexpected state.'}
          </div>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              padding: '10px 24px', borderRadius: 8, background: '#00B7FF', color: '#010817',
              border: 'none', fontWeight: 800, cursor: 'pointer', fontFamily: 'Orbitron, sans-serif',
              boxShadow: '0 0 20px rgba(0,183,255,0.4)'
            }}
          >
            REINITIALIZE SYSTEM
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Phase 2.5 — Cross-Device Presence: wake-on-push approvals via service worker.
// No permission prompt on load; subscribe only when permission was already granted.
registerPresenceWorker().then(() => subscribePresencePush());

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RootErrorBoundary>
      <App />
    </RootErrorBoundary>
  </StrictMode>,
)
