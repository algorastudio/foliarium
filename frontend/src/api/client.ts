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

export const getMe = () =>
  request<{ user_id: number; username: string; ruolo: string }>('/auth/me')

// ── Comuni & Località ─────────────────────────────────────────────────────

export interface Comune {
  id: number
  nome: string
  provincia: string
}

export interface Localita {
  id: number
  nome: string
  tipologia_stradale: string | null
}

export const getComuni = () => request<Comune[]>('/comuni')
export const getLocalita = (comuneId: number) =>
  request<Localita[]>(`/comuni/${comuneId}/localita`)

// ── Partite ────────────────────────────────────────────────────────────────

export interface Partita {
  id: number
  comune_nome: string
  numero_partita: number
  suffisso_partita: string | null
  tipo: string
  stato: string
  data_impianto?: string | null
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

export interface Possessore_PP {
  id: number
  nome_completo: string
  titolo: string | null
  quota: string | null
}

export interface Immobile {
  id: number
  natura: string
  numero_piani: number | null
  numero_vani: number | null
  consistenza: string | null
  classificazione: string | null
  localita_nome: string
  tipologia_stradale: string | null
}

export interface Variazione {
  id: number
  tipo: string
  data_variazione: string | null
  numero_riferimento: string | null
  partita_origine_id: number | null
  partita_destinazione_id: number | null
  origine_numero_partita: number | null
  origine_comune_nome: string | null
  destinazione_numero_partita: number | null
  destinazione_comune_nome: string | null
  tipo_contratto: string | null
  data_contratto: string | null
  notaio: string | null
}

export interface PartitaDetail {
  id: number
  numero_partita: number
  suffisso_partita: string | null
  tipo: string
  stato: string
  data_impianto: string | null
  data_chiusura: string | null
  numero_provenienza: number | null
  comune_nome: string
  comune_id: number
  possessori: Possessore_PP[]
  immobili: Immobile[]
  variazioni: Variazione[]
}

export const getPartita = (id: number) =>
  request<PartitaDetail>(`/partite/${id}`)

export interface CreatePartitaPayload {
  comune_id: number
  numero_partita: number
  suffisso_partita?: string
  data_impianto?: string
  tipo?: string
  stato?: string
  numero_provenienza?: number
}

export const createPartita = (payload: CreatePartitaPayload) =>
  request<{ id: number }>('/partite', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export interface AddImmobilePayload {
  localita_nome: string
  tipologia_stradale?: string
  natura: string
  numero_piani?: number
  numero_vani?: number
  consistenza?: string
  classificazione?: string
}

export const addImmobile = (partitaId: number, payload: AddImmobilePayload) =>
  request<{ id: number }>(`/partite/${partitaId}/immobili`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const deleteImmobile = (partitaId: number, immobileId: number) =>
  request<void>(`/partite/${partitaId}/immobili/${immobileId}`, { method: 'DELETE' })

export interface AddVariazionePayload {
  tipo: string
  data_variazione: string
  partita_destinazione_id?: number
  numero_riferimento?: string
  nominativo_riferimento?: string
}

export const addVariazione = (partitaId: number, payload: AddVariazionePayload) =>
  request<{ id: number }>(`/partite/${partitaId}/variazioni`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const deleteVariazione = (partitaId: number, variazioneId: number) =>
  request<void>(`/partite/${partitaId}/variazioni/${variazioneId}`, { method: 'DELETE' })

export interface CreatePossessorePayload {
  nome_completo: string
  cognome_nome?: string
  paternita?: string
  comune_id: number
}

export const createPossessore = (payload: CreatePossessorePayload) =>
  request<{ id: number }>('/possessori', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

// ── Possessori ─────────────────────────────────────────────────────────────

export interface Possessore {
  id: number
  nome_completo: string
  cognome_nome: string
  paternita: string | null
}

export const searchPossessori = (q: string) =>
  request<Possessore[]>(`/possessori?q=${encodeURIComponent(q)}`)

// ── Dashboard / Analytics ──────────────────────────────────────────────────

export interface DashboardStats {
  totale_partite: number
  totale_comuni: number
  totale_possessori: number
  totale_immobili: number
  per_comune: Array<{ comune?: string; comune_nome?: string; nome?: string; num_partite: number }>
}

export const getDashboardStats = () => request<DashboardStats>('/dashboard/stats')

export interface AnalyticsData {
  kpi: {
    partite: number
    particelle: number
    variazioni: number
    utenti_attivi: number
  }
  top_comuni: Array<{ comune: string; num_partite: number }>
  distribuzione_documenti: Array<{ label: string; value: number; pct: number }>
  qualita_dati: { completezza_pct: number; duplicati_pct: number }
}

export const getAnalytics = () => request<AnalyticsData>('/dashboard/analytics')

// ── Genealogia ─────────────────────────────────────────────────────────────

export interface GenealogiaNode {
  id: number
  numero_partita: number
  suffisso_partita: string | null
  tipo: string
  stato: string
  comune_nome: string
  data_impianto: string | null
  data_chiusura: string | null
  possessori: string | null
  tipo_variazione?: string | null
  data_variazione?: string | null
  nominativo_riferimento?: string | null
}

export interface Genealogia {
  partita: GenealogiaNode | null
  predecessori: GenealogiaNode[]
  successori: GenealogiaNode[]
}

export const getGenealogia = (partitaId: number) =>
  request<Genealogia>(`/genealogia/${partitaId}`)

// ── Timeline partita ───────────────────────────────────────────────────────

export interface TimelineEvent {
  data: string
  tipo: string
  label: string
  dettagli: string
  partita_origine?: number
  partita_destinazione?: number
}

export const getPartitaTimeline = (partitaId: number) =>
  request<{ partita_id: number; eventi: TimelineEvent[] }>(`/timeline/partita/${partitaId}`)

// ── Audit ──────────────────────────────────────────────────────────────────

export interface AuditEntry {
  id: number
  timestamp: string
  username: string | null
  tabella: string | null
  operazione: string | null
  operazione_label: string | null
  record_id: number | null
  dettagli: string | null
  client_ip?: string | null
}

export interface AuditPage {
  items: AuditEntry[]
  total: number
  page: number
  page_size: number
}

export interface AuditSummary {
  azioni_oggi: number
  utenti_attivi: number
  export_effettuati: number
  anomalie: number
}

export const getAuditLog = (params: {
  operation?: string
  username?: string
  page?: number
  page_size?: number
} = {}) => {
  const qs = new URLSearchParams()
  if (params.operation) qs.set('operation', params.operation)
  if (params.username) qs.set('username', params.username)
  qs.set('page', String(params.page ?? 1))
  qs.set('page_size', String(params.page_size ?? 50))
  return request<AuditPage>(`/audit?${qs}`)
}

export const getAuditSummary = () => request<AuditSummary>('/audit/summary')

// ── Possessori detail ──────────────────────────────────────────────────────

export interface PossessoreDetail {
  id: number
  nome_completo: string
  cognome_nome: string
  paternita: string | null
  partite: Array<{
    id: number
    numero_partita: number
    suffisso_partita: string | null
    comune_nome: string
    tipo: string
    stato: string
    titolo: string | null
    quota: string | null
  }>
}

export const getPossessore = (id: number) =>
  request<PossessoreDetail>(`/possessori/${id}`)
