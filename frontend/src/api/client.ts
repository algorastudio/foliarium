const BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('foliarium_token')
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ── Auth ───────────────────────────────────────────────────────────────────

export interface LoginResponse {
  token: string
  user_id: number
  username: string
  nome_completo: string
  ruolo: string
}

export const login = (username: string, password: string) =>
  request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })

export const logout = () => request('/auth/logout', { method: 'POST' })

export const getMe = () => request<{ user_id: number; username: string; ruolo: string }>('/auth/me')

// ── Comuni ─────────────────────────────────────────────────────────────────

export interface Comune {
  id: number
  nome: string
  provincia: string
}

export const getComuni = () => request<Comune[]>('/comuni')

// ── Partite ────────────────────────────────────────────────────────────────

export interface Partita {
  id: number
  comune_nome: string
  numero_partita: number
  suffisso_partita: string | null
  tipo: string
  stato: string
}

export interface SearchPartiteParams {
  comune_id?: number
  numero_partita?: number
  possessore?: string
  immobile_natura?: string
  suffisso?: string
}

export const searchPartite = (params: SearchPartiteParams) => {
  const qs = new URLSearchParams()
  if (params.comune_id != null) qs.set('comune_id', String(params.comune_id))
  if (params.numero_partita != null) qs.set('numero_partita', String(params.numero_partita))
  if (params.possessore) qs.set('possessore', params.possessore)
  if (params.immobile_natura) qs.set('immobile_natura', params.immobile_natura)
  if (params.suffisso) qs.set('suffisso', params.suffisso)
  return request<Partita[]>(`/partite?${qs}`)
}

export const getPartita = (id: number) => request<Record<string, unknown>>(`/partite/${id}`)

// ── Possessori ─────────────────────────────────────────────────────────────

export interface Possessore {
  id: number
  nome_completo: string
  cognome_nome: string
  paternita: string | null
}

export const searchPossessori = (q: string) =>
  request<Possessore[]>(`/possessori?q=${encodeURIComponent(q)}`)

// ── Dashboard ──────────────────────────────────────────────────────────────

export interface DashboardStats {
  totale_partite: number
  totale_comuni: number
  per_comune: Array<{ comune_nome?: string; nome?: string; num_partite: number }>
}

export const getDashboardStats = () => request<DashboardStats>('/dashboard/stats')
