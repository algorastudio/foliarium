export interface Comune {
  id: number;
  nome: string;
  provincia: string;
}

export interface Partita {
  id: number;
  comune_nome: string;
  numero_partita: number;
  suffisso_partita: string | null;
  tipo: string;
  stato: string;
  data_impianto?: string | null;
}

export interface PossessorePartita {
  id: number;
  nome_completo: string;
  titolo: string | null;
  quota: string | null;
}

export interface Immobile {
  id: number;
  natura: string;
  numero_piani: number | null;
  numero_vani: number | null;
  consistenza: string | null;
  classificazione: string | null;
  localita_nome: string;
  tipologia_stradale: string | null;
}

export interface Variazione {
  id: number;
  tipo: string;
  data_variazione: string | null;
  numero_riferimento: string | null;
  partita_origine_id: number | null;
  partita_destinazione_id: number | null;
  origine_numero_partita: number | null;
  origine_comune_nome: string | null;
  destinazione_numero_partita: number | null;
  destinazione_comune_nome: string | null;
  tipo_contratto: string | null;
  notaio: string | null;
}

export interface PartitaDetail extends Partita {
  data_chiusura: string | null;
  numero_provenienza: number | null;
  comune_id: number;
  possessori: PossessorePartita[];
  immobili: Immobile[];
  variazioni: Variazione[];
}

export interface Possessore {
  id: number;
  nome_completo: string;
  cognome_nome: string;
  paternita: string | null;
}

export interface DashboardStats {
  totale_partite: number;
  totale_comuni: number;
  totale_possessori: number;
  totale_immobili: number;
  per_comune: Array<{ comune?: string; comune_nome?: string; nome?: string; num_partite: number }>;
}

export interface AnalyticsData {
  kpi: { partite: number; particelle: number; variazioni: number; utenti_attivi: number };
  top_comuni: Array<{ comune: string; num_partite: number }>;
  distribuzione_documenti: Array<{ label: string; value: number; pct: number }>;
  qualita_dati: { completezza_pct: number; duplicati_pct: number };
}

export interface LoginResponse {
  token: string;
  user_id: number;
  username: string;
  nome_completo: string;
  ruolo: string;
}
