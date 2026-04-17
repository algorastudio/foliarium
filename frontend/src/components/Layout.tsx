import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Search, FilePlus, Users, FileText,
  BarChart2, Settings, LogOut, ChevronDown, ChevronRight,
} from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../AuthContext'
import { logout } from '../api/client'

const NAV = [
  { group: 'Consultazione', items: [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/partite', label: 'Ricerca Partite', icon: Search },
  ]},
  { group: 'Inserimento', items: [
    { to: '/nuova-partita', label: 'Nuova Partita', icon: FilePlus },
    { to: '/possessori', label: 'Possessori', icon: Users },
  ]},
  { group: 'Report', items: [
    { to: '/documenti', label: 'Documenti', icon: FileText },
    { to: '/statistiche', label: 'Statistiche', icon: BarChart2 },
  ]},
]

function SidebarGroup({ group, items }: typeof NAV[0]) {
  const [open, setOpen] = useState(true)
  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-200/60 hover:text-indigo-100"
      >
        {group}
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && items.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex items-center gap-3 mx-2 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive
                ? 'bg-white/15 text-white font-medium'
                : 'text-indigo-100 hover:bg-white/10 hover:text-white'
            }`
          }
        >
          <Icon size={16} />
          {label}
        </NavLink>
      ))}
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

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[220px] flex-shrink-0 bg-[#3f51b5] flex flex-col">
        {/* Logo */}
        <div className="h-12 flex items-center px-5 border-b border-white/10">
          <span className="text-white font-semibold text-sm tracking-wide">🌿 Foliarium</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-3 space-y-1">
          {NAV.map(g => <SidebarGroup key={g.group} {...g} />)}
        </nav>

        {/* User + logout */}
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2 mb-2 px-2">
            <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-xs font-bold">
              {user?.nome_completo?.[0]?.toUpperCase() ?? '?'}
            </div>
            <div className="min-w-0">
              <p className="text-white text-xs font-medium truncate">{user?.nome_completo}</p>
              <p className="text-indigo-200/60 text-[10px] capitalize">{user?.ruolo}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-indigo-100 hover:bg-white/10 hover:text-white text-xs transition-colors"
          >
            <LogOut size={14} />
            Esci
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-12 bg-white border-b border-gray-200 flex items-center px-6 gap-3 flex-shrink-0">
          <Settings size={15} className="text-gray-400" />
          <span className="text-sm text-gray-500 flex-1">Archivio Catastale Storico — Provincia di Savona</span>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6 bg-[#f5f5f5]">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
