import { useState, useMemo, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  searchPartite,
  getComuni,
  createPartita,
  type Partita,
  type CreatePartitaPayload,
} from '../api/client'
import {
  Card,
  Button,
  FilterChip,
  SectionHeader,
  MiniTag,
} from '../components/ui'

const PERIODI: Array<{ key: string; label: string; min?: number; max?: number }> = [
  { key: 'tutti', label: 'Tutti i periodi' },
  { key: '1800-1850', label: '1800–1850', min: 1800, max: 1850 },
  { key: '1851-1900', label: '1851–1900', min: 1851, max: 1900 },
  { key: '1901-1950', label: '1901–1950', min: 1901, max: 1950 },
]

const TIPI: Array<{ key: string; label: string }> = [
  { key: 'tutti', label: 'Tutti i tipi' },
  { key: 'principale', label: 'Principale' },
  { key: 'secondaria', label: 'Secondaria' },
]

function getYear(p: Partita): number | null {
  if (!p.data_impianto) return null
  const m = p.data_impianto.match(/^(\d{4})/)
  return m ? Number(m[1]) : null
}

function ResultRow({
  p,
  onSelect,
  selected,
}: {
  p: Partita
  onSelect: () => void
  selected: boolean
}) {
  const year = getYear(p)
  return (
    <div
      onClick={onSelect}
      style={{
        display: 'flex',
        gap: 12,
        alignItems: 'flex-start',
        padding: 12,
        background: 'var(--surface)',
        borderRadius: 'var(--radius-md)',
        border: selected ? '0.5px solid var(--purple)' : '0.5px solid var(--border)',
        cursor: 'pointer',
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 500,
          color: 'var(--purple)',
          background: 'var(--purple-light)',
          padding: '3px 7px',
          borderRadius: 4,
          whiteSpace: 'nowrap',
          marginTop: 2,
        }}
      >
        {year ?? '—'}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', marginBottom: 3 }}>
          Partita {p.numero_partita}
          {p.suffisso_partita ? `/${p.suffisso_partita}` : ''} — {p.comune_nome}{' '}
          <span
            style={{
              fontSize: 11,
              padding: '2px 6px',
              borderRadius: 4,
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              marginLeft: 6,
            }}
          >
            {p.tipo}
          </span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Stato: {p.stato} · ID {p.id}
        </div>
      </div>
      <span style={{ fontSize: 11, color: 'var(--purple)', alignSelf: 'center', flexShrink: 0 }}>→</span>
    </div>
  )
}

// ── NuovaPartita modal ────────────────────────────────────────────────────

interface NuovaPartitaModalProps {
  onClose: () => void
}

function NuovaPartitaModal({ onClose }: NuovaPartitaModalProps) {
  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })
  const qc = useQueryClient()
  const navigate = useNavigate()

  const [comuneId, setComuneId] = useState<string>('')
  const [numero, setNumero] = useState('')
  const [suffisso, setSuffisso] = useState('')
  const [tipo, setTipo] = useState('Principale')
  const [stato, setStato] = useState('attiva')
  const [dataImpianto, setDataImpianto] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (payload: CreatePartitaPayload) => createPartita(payload),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['archivio-search'] })
      onClose()
      navigate(`/partite/${result.id}`)
    },
    onError: (e: Error) => setError(e.message),
  })

  const handleSubmit = (ev: FormEvent) => {
    ev.preventDefault()
    setError(null)
    if (!comuneId) return setError('Seleziona un comune.')
    if (!numero || isNaN(Number(numero))) return setError('Numero partita non valido.')
    mutation.mutate({
      comune_id: Number(comuneId),
      numero_partita: Number(numero),
      suffisso_partita: suffisso || undefined,
      tipo,
      stato,
      data_impianto: dataImpianto || undefined,
    })
  }

  const fieldStyle = {
    width: '100%',
    padding: '7px 10px',
    border: '0.5px solid var(--border-md)',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    background: 'var(--surface)',
    color: 'var(--text)',
  }

  const labelStyle = {
    fontSize: 12,
    color: 'var(--text-secondary)',
    display: 'block' as const,
    marginBottom: 4,
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius-lg)',
          padding: 24,
          width: 440,
          maxWidth: '95vw',
          boxShadow: '0 8px 32px rgba(0,0,0,0.16)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <span style={{ fontSize: 15, fontWeight: 500 }}>Nuova partita</span>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text-secondary)', lineHeight: 1 }}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={labelStyle}>Comune *</label>
            <select value={comuneId} onChange={(e) => setComuneId(e.target.value)} style={fieldStyle}>
              <option value="">— Seleziona —</option>
              {(comuni ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.nome} ({c.provincia})</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={labelStyle}>N. partita *</label>
              <input
                type="number"
                value={numero}
                onChange={(e) => setNumero(e.target.value)}
                placeholder="es. 1234"
                style={fieldStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>Suffisso</label>
              <input
                type="text"
                value={suffisso}
                onChange={(e) => setSuffisso(e.target.value)}
                placeholder="es. A"
                style={fieldStyle}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={labelStyle}>Tipo</label>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)} style={fieldStyle}>
                <option>Principale</option>
                <option>Secondaria</option>
              </select>
            </div>
            <div>
              <label style={labelStyle}>Stato</label>
              <select value={stato} onChange={(e) => setStato(e.target.value)} style={fieldStyle}>
                <option value="attiva">Attiva</option>
                <option value="chiusa">Chiusa</option>
              </select>
            </div>
          </div>

          <div>
            <label style={labelStyle}>Data impianto</label>
            <input
              type="date"
              value={dataImpianto}
              onChange={(e) => setDataImpianto(e.target.value)}
              style={fieldStyle}
            />
          </div>

          {error && (
            <div style={{ fontSize: 12, color: 'var(--coral-text)', padding: '6px 10px', background: 'var(--coral-light)', borderRadius: 6 }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
            <Button onClick={onClose}>Annulla</Button>
            <Button variant="primary" type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creazione…' : 'Crea partita'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function Archivio() {
  const navigate = useNavigate()
  const [comuneId, setComuneId] = useState<number | undefined>(undefined)
  const [numero, setNumero] = useState<string>('')
  const [possessore, setPossessore] = useState<string>('')
  const [periodo, setPeriodo] = useState<string>('tutti')
  const [tipoFiltro, setTipoFiltro] = useState<string>('tutti')
  const [submitted, setSubmitted] = useState(false)
  const [showNuova, setShowNuova] = useState(false)

  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })

  const params = useMemo(
    () => ({
      comune_id: comuneId,
      numero_partita: numero ? Number(numero) : undefined,
      possessore: possessore || undefined,
    }),
    [comuneId, numero, possessore]
  )

  const { data: results, isLoading } = useQuery({
    queryKey: ['archivio-search', params],
    queryFn: () => searchPartite(params),
    enabled: submitted,
  })

  const filtered = (results ?? []).filter((p) => {
    const y = getYear(p)
    const periodoMatch = (() => {
      const pp = PERIODI.find((x) => x.key === periodo)
      if (!pp || !pp.min || !pp.max) return true
      if (y === null) return false
      return y >= pp.min && y <= pp.max
    })()
    const tipoMatch =
      tipoFiltro === 'tutti' ||
      (p.tipo || '').toLowerCase().includes(tipoFiltro)
    return periodoMatch && tipoMatch
  })

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
  }

  return (
    <div>
      {showNuova && <NuovaPartitaModal onClose={() => setShowNuova(false)} />}

      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select
          value={comuneId ?? ''}
          onChange={(e) =>
            setComuneId(e.target.value ? Number(e.target.value) : undefined)
          }
          style={{
            flex: '0 0 200px',
            padding: '8px 12px',
            border: '0.5px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            background: 'var(--surface)',
            color: 'var(--text)',
          }}
        >
          <option value="">Tutti i comuni</option>
          {(comuni ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.nome} ({c.provincia})
            </option>
          ))}
        </select>
        <input
          type="text"
          value={possessore}
          onChange={(e) => setPossessore(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setSubmitted(true)}
          placeholder="Cerca per possessore o cognome…"
          style={{
            flex: 1,
            padding: '8px 12px',
            border: '0.5px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            background: 'var(--surface)',
            color: 'var(--text)',
          }}
        />
        <input
          type="number"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setSubmitted(true)}
          placeholder="N. partita"
          style={{
            flex: '0 0 110px',
            padding: '8px 12px',
            border: '0.5px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            background: 'var(--surface)',
            color: 'var(--text)',
          }}
        />
        <Button variant="primary" onClick={() => handleSearch(new Event('submit') as unknown as FormEvent)}>
          Cerca
        </Button>
        <Button
          onClick={() => setShowNuova(true)}
          style={{ flexShrink: 0 }}
        >
          + Nuova
        </Button>
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        {PERIODI.map((p) => (
          <FilterChip
            key={p.key}
            active={periodo === p.key}
            onClick={() => setPeriodo(p.key)}
          >
            {p.label}
          </FilterChip>
        ))}
        {TIPI.slice(1).map((t) => (
          <FilterChip
            key={t.key}
            active={tipoFiltro === t.key}
            onClick={() =>
              setTipoFiltro(tipoFiltro === t.key ? 'tutti' : t.key)
            }
          >
            {t.label}
          </FilterChip>
        ))}
      </div>

      <SectionHeader
        title={
          submitted
            ? `Risultati — ${filtered.length} ${
                filtered.length === 1 ? 'partita trovata' : 'partite trovate'
              }`
            : 'Risultati'
        }
        right={submitted && filtered.length > 0 ? <MiniTag>Clicca per aprire</MiniTag> : undefined}
      />

      {!submitted && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Avvia una ricerca per visualizzare le partite.
          </p>
        </Card>
      )}
      {submitted && isLoading && (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Ricerca in corso…</p>
      )}
      {submitted && !isLoading && filtered.length === 0 && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Nessun risultato per i criteri selezionati.
          </p>
        </Card>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filtered.slice(0, 100).map((p) => (
          <ResultRow
            key={p.id}
            p={p}
            selected={false}
            onSelect={() => navigate(`/partite/${p.id}`)}
          />
        ))}
      </div>
      {filtered.length > 100 && (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center', marginTop: 12 }}>
          Mostrati i primi 100 risultati. Affina la ricerca per risultati più specifici.
        </p>
      )}
    </div>
  )
}
