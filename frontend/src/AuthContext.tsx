import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface UserInfo {
  user_id: number
  username: string
  nome_completo: string
  ruolo: string
}

interface AuthCtx {
  user: UserInfo | null
  token: string | null
  setAuth: (token: string, user: UserInfo) => void
  clearAuth: () => void
}

const Ctx = createContext<AuthCtx>({
  user: null, token: null,
  setAuth: () => {}, clearAuth: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('foliarium_token'))
  const [user, setUser] = useState<UserInfo | null>(() => {
    const raw = localStorage.getItem('foliarium_user')
    return raw ? JSON.parse(raw) : null
  })

  const setAuth = (t: string, u: UserInfo) => {
    localStorage.setItem('foliarium_token', t)
    localStorage.setItem('foliarium_user', JSON.stringify(u))
    setToken(t)
    setUser(u)
  }

  const clearAuth = () => {
    localStorage.removeItem('foliarium_token')
    localStorage.removeItem('foliarium_user')
    setToken(null)
    setUser(null)
  }

  return <Ctx.Provider value={{ user, token, setAuth, clearAuth }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
