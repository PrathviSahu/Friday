import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          position: 'absolute',
          inset: 0,
          zIndex: 9999,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(2, 3, 10, 0.85)',
          backdropFilter: 'blur(16px)',
          fontFamily: 'Inter, system-ui, sans-serif'
        }}>
          <div style={{
            background: 'rgba(1, 16, 24, 0.95)',
            border: '1px solid rgba(255, 68, 68, 0.35)',
            boxShadow: '0 8px 32px rgba(255, 68, 68, 0.15)',
            borderRadius: 14,
            padding: '24px 32px',
            maxWidth: 380,
            textAlign: 'center'
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: 'rgba(255, 68, 68, 0.15)',
              color: '#ff4444',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              fontWeight: 'bold',
              margin: '0 auto 16px',
              border: '1px solid rgba(255, 68, 68, 0.4)'
            }}>
              ⚠️
            </div>
            <h3 style={{
              margin: '0 0 8px',
              fontFamily: 'Orbitron, sans-serif',
              fontSize: 13,
              fontWeight: 700,
              color: '#ff4444',
              letterSpacing: '0.15em',
              textTransform: 'uppercase'
            }}>
              Console Exception
            </h3>
            <p style={{
              margin: '0 0 20px',
              fontSize: 12,
              color: '#94a3b8',
              lineHeight: 1.5
            }}>
              Excuse me Prem, I encountered a minor layout interruption in this workspace module. 
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 6,
                background: 'rgba(255, 68, 68, 0.1)',
                border: '1px solid rgba(255, 68, 68, 0.35)',
                color: '#ff6666',
                fontFamily: 'Orbitron, sans-serif',
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: '0.1em',
                cursor: 'pointer',
                transition: 'all 150ms ease',
              }}
            >
              Restore Console
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
