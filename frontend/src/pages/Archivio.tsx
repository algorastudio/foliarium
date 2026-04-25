import { useState, useMemo, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  searchPartite,
  getComuni,
  getPartitaTimeline,
  type Partita,
} from '../api/client'
import {
  Card,
  Button,
  FilterChip,
  SectionHeader,
  MiniTag,
  TwoCol,
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
    </div>
  )
}

function Timeline({ partitaId }: { partitaId: number | null }) {
  const { data, isLoading } = useQuery({
    queryKey: ['timeline', partitaId],
    queryFn: () => getPartitaTimeline(partitaId!),
    enabled: partitaId !== null,
  })

  if (partitaId === null) {
    return (
      <Card title="Cronologia proprietà">
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Seleziona una partita per visualizzare la cronologia.
        </p>
      </Card>
    )
  }

  return (
    <Card title={`Cronologia proprietà — Partita ${partitaId}`}>
      {isLoading && (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Caricamento…</p>
      )}
      {!isLoading && (!data || data.eventi.length === 0) && (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Nessun evento storico registrato.
        </p>
      )}
      {!isLoading && data && data.eventi.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginTop: 8 }}>
          {data.eventi.map((e, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                gap: 12,
                alignItems: 'flex-start',
                padding: '10px 0',
                borderLeft:
                  i === data.eventi.length - 1
                    ? '2px solid transparent'
                    : '2px solid var(--border)',
                paddingLeft: 16,
                position: 'relative',
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: 'var(--purple)',
                  border: '2px solid var(--surface)',
                  position: 'absolute',
                  left: -5,
                  top: 14,
                }}
              />
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', minWidth: 50, marginTop: 1 }}>
                {(e.data || '').slice(0, 4)}
              </div>
              <div>
                <div style={{ fontSize: 13, color: 'var(--text)' }}>{e.label}</div>
                {e.dettagli && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {e.dettagli}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

export default function Archivio() {
  const [comuneId, setComuneId] = useState<number | undefined>(undefined)
  const [numero, setNumero] = useState<string>('')
  const [possessore, setPossessore] = useState<string>('')
  const [periodo, setPeriodo] = useState<string>('tutti')
  const [tipoFiltro, setTipoFiltro] = useState<string>('tutti')
  const [submitted, setSubmitted] = useState(false)
  const [selected, setSelected] = useState<Partita | null>(null)

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

      <TwoCol>
        <div>
          <SectionHeader
            title={
              submitted
                ? `Risultati — ${filtered.length} ${
                    filtered.length === 1 ? 'partita trovata' : 'partite trovate'
                  }`
                : 'Risultati'
            }
            right={<MiniTag>Ordinati per data</MiniTag>}
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
            {filtered.slice(0, 50).map((p) => (
              <ResultRow
                key={p.id}
                p={p}
                selected={selected?.id === p.id}
                onSelect={() => setSelected(p)}
              />
            ))}
          </div>
        </div>

        <Timeline partitaId={selected?.id ?? null} />
      </TwoCol>
    </div>
  )
}
