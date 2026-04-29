import { useState, useMemo, useEffect, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  useReactTable, getCoreRowModel, getSortedRowModel, getFilteredRowModel,
  flexRender, createColumnHelper, type SortingState,
} from '@tanstack/react-table'
import {
  searchPartite, getComuni, createPartita,
  type Partita, type CreatePartitaPayload,
} from '../api/client'
import { Card, Button, FilterChip, SectionHeader, MiniTag, StatusChip } from '../components/ui'

const PERIODI: Array<{ key: string; label: string; min?: number; max?: number }> = [
  { key: 'tutti', label: 'Tutti i periodi' },
  { key: '1800-1850', label: '1800–1850', min: 1800, max: 1850 },
  { key: '1851-1900', label: '1851–1900', min: 1851, max: 1900 },
  { key: '1901-1950', label: '1901–1950', min: 1901, max: 1950 },
]

function getYear(p: Partita): number | null {
  if (!p.data_impianto) return null
  const m = p.data_impianto.match(/^(\d{4})/)
  return m ? Number(m[1]) : null
}

// ── TanStack Table ─────────────────────────────────────────────────────────

const colHelper = createColumnHelper<Partita>()

const columns = [
  colHelper.accessor((row) => getYear(row), {
    id: 'anno',
    header: 'Anno',
    cell: (info) => {
      const v = info.getValue()
      return (
        <span style={{
          fontSize: 11, fontWeight: 500, color: 'var(--purple)',
          background: 'var(--purple-light)', padding: '2px 6px', borderRadius: 4,
        }}>
          {v ?? '—'}
        </span>
      )
    },
    sortingFn: (a, b) => (getYear(a.original) ?? 0) - (getYear(b.original) ?? 0),
  }),
  colHelper.accessor('numero_partita', {
    header: 'N. Partita',
    cell: (info) => (
      <span style={{ fontWeight: 500 }}>
        {info.getValue()}{info.row.original.suffisso_partita ? `/${info.row.original.suffisso_partita}` : ''}
      </span>
    ),
  }),
  colHelper.accessor('comune_nome', {
    header: 'Comune',
    cell: (info) => info.getValue(),
  }),
  colHelper.accessor('tipo', {
    header: 'Tipo',
    cell: (info) => <MiniTag>{info.getValue()}</MiniTag>,
  }),
  colHelper.accessor('stato', {
    header: 'Stato',
    cell: (info) => (
      <StatusChip variant={info.getValue()?.toLowerCase() === 'attiva' ? 'ok' : 'neutral'}>
        {info.getValue()}
      </StatusChip>
    ),
  }),
]

function SortIcon({ dir }: { dir: 'asc' | 'desc' | false }) {
  if (!dir) return <span style={{ color: 'var(--border-md)', fontSize: 10 }}>↕</span>
  return <span style={{ color: 'var(--purple)', fontSize: 10 }}>{dir === 'asc' ? '↑' : '↓'}</span>
}

function ResultTable({ data, onRowClick }: { data: Partita[]; onRowClick: (p: Partita) => void }) {
  const [sorting, setSorting] = useState<SortingState>([{ id: 'anno', desc: false }])

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} style={{ borderBottom: '0.5px solid var(--border)' }}>
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  style={{
                    textAlign: 'left', padding: '8px 10px', fontWeight: 500,
                    color: 'var(--text-secondary)', fontSize: 12, whiteSpace: 'nowrap',
                    cursor: header.column.getCanSort() ? 'pointer' : 'default',
                    userSelect: 'none',
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    <SortIcon dir={header.column.getIsSorted()} />
                  </span>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick(row.original)}
              style={{
                borderBottom: '0.5px solid var(--border)',
                cursor: 'pointer',
                transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--purple-light)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = '')}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} style={{ padding: '9px 10px' }}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── NuovaPartita modal ────────────────────────────────────────────────────

function NuovaPartitaModal({ onClose }: { onClose: () => void }) {
  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })
  const qc = useQueryClient()
  const navigate = useNavigate()

  const [comuneId, setComuneId] = useState('')
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
      tipo, stato,
      data_impianto: dataImpianto || undefined,
    })
  }

  const fs = {
    width: '100%', padding: '7px 10px', border: '0.5px solid var(--border-md)',
    borderRadius: 'var(--radius-md)', fontSize: 13, background: 'var(--surface)', color: 'var(--text)',
  }
  const ls = { fontSize: 12, color: 'var(--text-secondary)', display: 'block' as const, marginBottom: 4 }

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 24, width: 440, maxWidth: '95vw', boxShadow: '0 8px 32px rgba(0,0,0,0.16)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <span style={{ fontSize: 15, fontWeight: 500 }}>Nuova partita</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text-secondary)', lineHeight: 1 }}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={ls}>Comune *</label>
            <select value={comuneId} onChange={(e) => setComuneId(e.target.value)} style={fs}>
              <option value="">— Seleziona —</option>
              {(comuni ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome} ({c.provincia})</option>)}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={ls}>N. partita *</label>
              <input type="number" value={numero} onChange={(e) => setNumero(e.target.value)} placeholder="es. 1234" style={fs} />
            </div>
            <div>
              <label style={ls}>Suffisso</label>
              <input type="text" value={suffisso} onChange={(e) => setSuffisso(e.target.value)} placeholder="es. A" style={fs} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={ls}>Tipo</label>
              <select value={tipo} onChange={(e) => setTipo(e.target.value)} style={fs}>
                <option>Principale</option>
                <option>Secondaria</option>
              </select>
            </div>
            <div>
              <label style={ls}>Stato</label>
              <select value={stato} onChange={(e) => setStato(e.target.value)} style={fs}>
                <option value="attiva">Attiva</option>
                <option value="chiusa">Chiusa</option>
              </select>
            </div>
          </div>
          <div>
            <label style={ls}>Data impianto</label>
            <input type="date" value={dataImpianto} onChange={(e) => setDataImpianto(e.target.value)} style={fs} />
          </div>
          {error && (
            <div style={{ fontSize: 12, color: 'var(--coral-text)', padding: '6px 10px', background: 'var(--coral-light)', borderRadius: 6 }}>{error}</div>
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

const PAGE_SIZE = 25

function exportCsv(rows: Partita[]) {
  const header = ['ID', 'Comune', 'N. Partita', 'Suffisso', 'Tipo', 'Stato', 'Data impianto']
  const lines = rows.map((r) => [
    r.id,
    r.comune_nome,
    r.numero_partita,
    r.suffisso_partita ?? '',
    r.tipo,
    r.stato,
    r.data_impianto ? r.data_impianto.slice(0, 10) : '',
  ].map(String).join(';'))
  const csv = [header.join(';'), ...lines].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `partite_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function Archivio() {
  const navigate = useNavigate()
  const [comuneId, setComuneId] = useState<number | undefined>(undefined)
  const [numero, setNumero] = useState('')
  const [possessore, setPossessore] = useState('')
  const [periodo, setPeriodo] = useState('tutti')
  const [tipoFiltro, setTipoFiltro] = useState('tutti')
  const [submitted, setSubmitted] = useState(false)
  const [showNuova, setShowNuova] = useState(false)
  const [page, setPage] = useState(1)

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

  const filtered = useMemo(() => {
    return (results ?? []).filter((p) => {
      const y = getYear(p)
      const pp = PERIODI.find((x) => x.key === periodo)
      const periodoOk = !pp?.min || (y !== null && y >= pp.min && y <= (pp.max ?? Infinity))
      const tipoOk = tipoFiltro === 'tutti' || (p.tipo || '').toLowerCase().includes(tipoFiltro)
      return periodoOk && tipoOk
    })
  }, [results, periodo, tipoFiltro])

  useEffect(() => { setPage(1) }, [periodo, tipoFiltro, results])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageSlice = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    setPage(1)
    setSubmitted(true)
  }

  return (
    <div>
      {showNuova && <NuovaPartitaModal onClose={() => setShowNuova(false)} />}

      {/* Search bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select
          value={comuneId ?? ''}
          onChange={(e) => setComuneId(e.target.value ? Number(e.target.value) : undefined)}
          style={{ flex: '0 0 200px', padding: '8px 12px', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-md)', fontSize: 13, background: 'var(--surface)', color: 'var(--text)' }}
        >
          <option value="">Tutti i comuni</option>
          {(comuni ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome} ({c.provincia})</option>)}
        </select>
        <input
          type="text"
          value={possessore}
          onChange={(e) => setPossessore(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setSubmitted(true)}
          placeholder="Cerca per possessore o cognome…"
          style={{ flex: 1, padding: '8px 12px', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-md)', fontSize: 13, background: 'var(--surface)', color: 'var(--text)' }}
        />
        <input
          type="number"
          value={numero}
          onChange={(e) => setNumero(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setSubmitted(true)}
          placeholder="N. partita"
          style={{ flex: '0 0 110px', padding: '8px 12px', border: '0.5px solid var(--border)', borderRadius: 'var(--radius-md)', fontSize: 13, background: 'var(--surface)', color: 'var(--text)' }}
        />
        <Button variant="primary" onClick={() => handleSearch(new Event('submit') as unknown as FormEvent)}>
          Cerca
        </Button>
        <Button onClick={() => setShowNuova(true)}>+ Nuova</Button>
        {submitted && filtered.length > 0 && (
          <Button onClick={() => exportCsv(filtered)}>↓ CSV</Button>
        )}
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        {PERIODI.map((p) => (
          <FilterChip key={p.key} active={periodo === p.key} onClick={() => setPeriodo(p.key)}>
            {p.label}
          </FilterChip>
        ))}
        {[{ key: 'principale', label: 'Principale' }, { key: 'secondaria', label: 'Secondaria' }].map((t) => (
          <FilterChip key={t.key} active={tipoFiltro === t.key} onClick={() => setTipoFiltro(tipoFiltro === t.key ? 'tutti' : t.key)}>
            {t.label}
          </FilterChip>
        ))}
      </div>

      <SectionHeader
        title={
          submitted
            ? `${filtered.length} ${filtered.length === 1 ? 'partita trovata' : 'partite trovate'}`
            : 'Risultati'
        }
        right={submitted && filtered.length > 0
          ? <MiniTag>Clicca intestazione per ordinare</MiniTag>
          : undefined}
      />

      {!submitted && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Avvia una ricerca per visualizzare le partite.</p>
        </Card>
      )}
      {submitted && isLoading && (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Ricerca in corso…</p>
      )}
      {submitted && !isLoading && filtered.length === 0 && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessun risultato per i criteri selezionati.</p>
        </Card>
      )}
      {submitted && !isLoading && filtered.length > 0 && (
        <>
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            <ResultTable data={pageSlice} onRowClick={(p) => navigate(`/partite/${p.id}`)} />
          </Card>
          {totalPages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginTop: 12 }}>
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={{
                  fontSize: 12, padding: '4px 12px', borderRadius: 'var(--radius-md)',
                  border: '0.5px solid var(--border-md)', background: 'var(--surface)',
                  cursor: page === 1 ? 'default' : 'pointer',
                  opacity: page === 1 ? 0.4 : 1, color: 'var(--text)',
                }}
              >
                ← Prec
              </button>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Pagina {page} di {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                style={{
                  fontSize: 12, padding: '4px 12px', borderRadius: 'var(--radius-md)',
                  border: '0.5px solid var(--border-md)', background: 'var(--surface)',
                  cursor: page === totalPages ? 'default' : 'pointer',
                  opacity: page === totalPages ? 0.4 : 1, color: 'var(--text)',
                }}
              >
                Succ →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
