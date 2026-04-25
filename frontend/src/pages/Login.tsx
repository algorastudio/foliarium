import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { login } from '../api/client'

export default function Login() {
  const { setAuth } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(username, password)
      setAuth(res.token, {
        user_id: res.user_id,
        username: res.username,
        nome_completo: res.nome_completo,
        ruolo: res.ruolo,
      })
      navigate('/archivio')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore di accesso')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100svh',
        background: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius-lg)',
          border: '0.5px solid var(--border)',
          padding: 32,
          width: '100%',
          maxWidth: 380,
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 8,
              background: 'var(--purple-dark)',
              margin: '0 auto 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg viewBox="0 0 16 16" width={22} height={22} fill="none">
              <rect x="2" y="2" width="5" height="5" rx="1" fill="white" opacity="0.9" />
              <rect x="9" y="2" width="5" height="5" rx="1" fill="white" opacity="0.6" />
              <rect x="2" y="9" width="5" height="5" rx="1" fill="white" opacity="0.6" />
              <rect x="9" y="9" width="5" height="5" rx="1" fill="white" opacity="0.3" />
            </svg>
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 500, color: 'var(--text)', margin: 0 }}>
            Foliarium
          </h1>
          <p
            style={{
              fontSize: 12,
              color: 'var(--text-secondary)',
              marginTop: 4,
            }}
          >
            Archivio Catastale Storico — Savona
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label
              style={{
                display: 'block',
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: 4,
              }}
            >
              Utente
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              placeholder="username"
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: 13,
                border: '0.5px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface)',
                color: 'var(--text)',
                outline: 'none',
              }}
            />
          </div>
          <div>
            <label
              style={{
                display: 'block',
                fontSize: 12,
                fontWeight: 500,
                color: 'var(--text-secondary)',
                marginBottom: 4,
              }}
            >
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: 13,
                border: '0.5px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                background: 'var(--surface)',
                color: 'var(--text)',
                outline: 'none',
              }}
            />
          </div>

          {error && (
            <div
              style={{
                background: 'var(--coral-light)',
                border: '0.5px solid rgba(163, 45, 45, 0.3)',
                color: 'var(--coral-text)',
                fontSize: 12,
                padding: '8px 10px',
                borderRadius: 'var(--radius-md)',
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '10px',
              fontSize: 13,
              fontWeight: 500,
              color: '#fff',
              background: 'var(--purple)',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1,
              marginTop: 4,
            }}
          >
            {loading ? 'Accesso in corso…' : 'Accedi'}
          </button>
        </form>
      </div>
    </div>
  )
}
