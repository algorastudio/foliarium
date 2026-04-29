import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { logout } from '../api/client'

const TABS = [
  { to: '/archivio', label: 'Consultazione archivio' },
  { to: '/possessori', label: 'Possessori' },
  { to: '/genealogia', label: 'Proprietà & genealogia' },
  { to: '/analytics', label: 'Dashboard analytics' },
  { to: '/audit', label: 'Audit & log' },
]

function BrandIcon() {
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: 6,
        background: 'var(--purple-dark)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      <svg viewBox="0 0 16 16" width={16} height={16} fill="none">
        <rect x="2" y="2" width="5" height="5" rx="1" fill="white" opacity="0.9" />
        <rect x="9" y="2" width="5" height="5" rx="1" fill="white" opacity="0.6" />
        <rect x="2" y="9" width="5" height="5" rx="1" fill="white" opacity="0.6" />
        <rect x="9" y="9" width="5" height="5" rx="1" fill="white" opacity="0.3" />
      </svg>
    </div>
  )
}

function Avatar({ initials }: { initials: string }) {
  return (
    <div
      style={{
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: 'var(--info-light)',
        color: 'var(--info-text)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 11,
        fontWeight: 500,
      }}
    >
      {initials}
    </div>
  )
}

export default function Layout() {
  const { user, clearAuth } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout().catch(() => {})
    clearAuth()
    navigate('/login')
  }

  const initials = (user?.nome_completo || user?.username || '?')
    .split(/\s+/)
    .map((s) => s[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div
      style={{
        background: 'var(--bg)',
        minHeight: '100vh',
        padding: 24,
      }}
    >
      <div
        className="shell"
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          background: 'var(--surface)',
          border: '0.5px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          overflow: 'hidden',
        }}
      >
        {/* Topbar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            borderBottom: '0.5px solid var(--border)',
            height: 52,
            background: 'var(--surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BrandIcon />
            <span
              style={{
                fontSize: 15,
                fontWeight: 500,
                letterSpacing: '-0.3px',
                color: 'var(--text)',
              }}
            >
              Foliarium
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              / Archivio di Stato di Savona
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span
              style={{
                fontSize: 11,
                padding: '3px 8px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-secondary)',
                border: '0.5px solid var(--border)',
              }}
            >
              v1.6.1 — web preview
            </span>
            {user && <Avatar initials={initials} />}
            <button
              onClick={handleLogout}
              style={{
                fontSize: 12,
                padding: '4px 10px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg)',
                color: 'var(--text-secondary)',
                border: '0.5px solid var(--border-md)',
                cursor: 'pointer',
              }}
            >
              Esci
            </button>
          </div>
        </div>

        {/* Nav tabs */}
        <div
          style={{
            display: 'flex',
            gap: 2,
            padding: '0 20px',
            borderBottom: '0.5px solid var(--border)',
            background: 'var(--surface)',
            overflowX: 'auto',
          }}
        >
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              style={({ isActive }) => ({
                padding: '10px 14px',
                fontSize: 13,
                color: isActive ? 'var(--text)' : 'var(--text-secondary)',
                fontWeight: isActive ? 500 : 400,
                cursor: 'pointer',
                borderBottom: isActive
                  ? '2px solid var(--purple)'
                  : '2px solid transparent',
                whiteSpace: 'nowrap',
                textDecoration: 'none',
                transition: 'color 0.15s',
              })}
            >
              {t.label}
            </NavLink>
          ))}
        </div>

        {/* Content */}
        <div
          style={{
            padding: 20,
            minHeight: 480,
            background: 'var(--bg-tertiary)',
          }}
        >
          <Outlet />
        </div>
      </div>
    </div>
  )
}
