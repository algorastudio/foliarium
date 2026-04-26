import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  searchPossessori, getPossessore, getComuni, createPossessore,
  type Possessore, type CreatePossessorePayload,
} from '../api/client'
import { Card, Button, SectionHeader, MiniTag, StatusChip } from '../components/ui'

function PossessoreRow({
  p,
  selected,
  onSelect,
}: {
  p: Possessore
  selected: boolean
  onSelect: () => void
}) {
  return (
    <div
      onClick={onSelect}
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '10px 12px',
        background: 'var(--surface)',
        borderRadius: 'var(--radius-md)',
        border: selected ? '0.5px solid var(--purple)' : '0.5px solid var(--border)',
        cursor: 'pointer',
        gap: 12,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>
          {p.nome_completo}
        </div>
        {p.paternita && (
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
            fu {p.paternita}
          </div>
        )}
      </div>
      <span style={{ fontSize: 11, color: 'var(--text-secondary)', flexShrink: 0 }}>ID {p.id}</span>
    </div>
  )
}

function PossessorePanel({ possessoreId }: { possessoreId: number }) {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['possessore', possessoreId],
    queryFn: () => getPossessore(possessoreId),
  })

  if (isLoading) {
    return (
      <Card title="Dettaglio possessore">
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Caricamento…</p>
      </Card>
    )
  }

  if (!data) return null

  return (
    <div>
      <Card style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 4 }}>{data.nome_completo}</div>
        {data.cognome_nome && data.cognome_nome !== data.nome_completo && (
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
            Cognome/nome: {data.cognome_nome}
          </div>
        )}
        {data.paternita && (
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Paternità: fu {data.paternita}
          </div>
        )}
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-secondary)' }}>
          ID possessore: {data.id}
        </div>
      </Card>

      <SectionHeader
        title={`Partite associate — ${data.partite.length}`}
        right={<MiniTag>Clicca per aprire</MiniTag>}
      />

      {data.partite.length === 0 && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessuna partita associata.</p>
        </Card>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.partite.map((pt) => (
          <div
            key={pt.id}
            onClick={() => navigate(`/partite/${pt.id}`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '10px 12px',
              background: 'var(--surface)',
              border: '0.5px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
            }}
          >
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>
                Partita {pt.numero_partita}
                {pt.suffisso_partita ? `/${pt.suffisso_partita}` : ''}{' '}
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 400 }}>
                  — {pt.comune_nome}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {pt.titolo && <span>{pt.titolo}</span>}
                {pt.titolo && pt.quota && <span> · </span>}
                {pt.quota && <span>Quota: {pt.quota}</span>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <MiniTag>{pt.tipo}</MiniTag>
              <StatusChip variant={pt.stato?.toLowerCase() === 'attiva' ? 'ok' : 'neutral'}>
                {pt.stato}
              </StatusChip>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── NuovoPossessore modal ─────────────────────────────────────────────────

function NuovoPossessoreModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: number) => void }) {
  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })
  const [nome, setNome] = useState('')
  const [cognomeNome, setCognomeNome] = useState('')
  const [paternita, setPaternita] = useState('')
  const [comuneId, setComuneId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (p: CreatePossessorePayload) => createPossessore(p),
    onSuccess: (r) => onCreated(r.id),
    onError: (e: Error) => setError(e.message),
  })

  const fs = {
    width: '100%', padding: '7px 10px', border: '0.5px solid var(--border-md)',
    borderRadius: 'var(--radius-md)', fontSize: 13, background: 'var(--surface)', color: 'var(--text)',
  }
  const ls = { fontSize: 12, color: 'var(--text-secondary)', display: 'block' as const, marginBottom: 4 }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!nome.trim()) return setError('Nome completo obbligatorio.')
    if (!comuneId) return setError('Seleziona un comune di riferimento.')
    mutation.mutate({
      nome_completo: nome.trim(),
      cognome_nome: cognomeNome.trim() || undefined,
      paternita: paternita.trim() || undefined,
      comune_id: Number(comuneId),
    })
  }

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius-lg)', padding: 24, width: 420, maxWidth: '95vw', boxShadow: '0 8px 32px rgba(0,0,0,0.16)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <span style={{ fontSize: 15, fontWeight: 500 }}>Nuovo possessore</span>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text-secondary)', lineHeight: 1 }}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={ls}>Nome completo *</label>
            <input style={fs} value={nome} onChange={(e) => setNome(e.target.value)} placeholder="es. Rossi Mario" />
          </div>
          <div>
            <label style={ls}>Cognome e nome (formato archivio)</label>
            <input style={fs} value={cognomeNome} onChange={(e) => setCognomeNome(e.target.value)} placeholder="es. Rossi Mario fu Giovanni" />
          </div>
          <div>
            <label style={ls}>Paternità</label>
            <input style={fs} value={paternita} onChange={(e) => setPaternita(e.target.value)} placeholder="es. Giovanni" />
          </div>
          <div>
            <label style={ls}>Comune di riferimento *</label>
            <select style={fs} value={comuneId} onChange={(e) => setComuneId(e.target.value)}>
              <option value="">— Seleziona —</option>
              {(comuni ?? []).map((c) => <option key={c.id} value={c.id}>{c.nome} ({c.provincia})</option>)}
            </select>
          </div>
          {error && <div style={{ fontSize: 12, color: 'var(--coral-text)', padding: '6px 10px', background: 'var(--coral-light)', borderRadius: 6 }}>{error}</div>}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
            <Button onClick={onClose}>Annulla</Button>
            <Button variant="primary" type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Creazione…' : 'Crea possessore'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Possessori() {
  const qc = useQueryClient()
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showNuovo, setShowNuovo] = useState(false)

  // Deep-link: /possessori?id=N apre direttamente la scheda
  useEffect(() => {
    const idParam = searchParams.get('id')
    if (idParam && !isNaN(Number(idParam))) {
      setSelectedId(Number(idParam))
    }
  }, [searchParams])

  const { data: results, isLoading } = useQuery({
    queryKey: ['possessori-search', query],
    queryFn: () => searchPossessori(query),
    enabled: submitted && query.length >= 2,
  })

  const handleSearch = () => {
    if (query.length >= 2) setSubmitted(true)
  }

  const handleCreated = (id: number) => {
    setShowNuovo(false)
    qc.invalidateQueries({ queryKey: ['possessori-search'] })
    setSelectedId(id)
  }

  return (
    <div>
      {showNuovo && <NuovoPossessoreModal onClose={() => setShowNuovo(false)} onCreated={handleCreated} />}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            if (submitted && e.target.value.length < 2) setSubmitted(false)
          }}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="Cerca per cognome, nome o paternità…"
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
        <Button variant="primary" onClick={handleSearch} disabled={query.length < 2}>
          Cerca
        </Button>
        <Button onClick={() => setShowNuovo(true)}>+ Nuovo</Button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.4fr)',
          gap: 12,
          alignItems: 'start',
        }}
      >
        {/* Results list */}
        <div>
          <SectionHeader
            title={
              submitted
                ? `${(results ?? []).length} ${(results ?? []).length === 1 ? 'possessore trovato' : 'possessori trovati'}`
                : 'Risultati'
            }
          />

          {!submitted && (
            <Card>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Inserisci almeno 2 caratteri per avviare la ricerca.
              </p>
            </Card>
          )}
          {submitted && isLoading && (
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Ricerca in corso…</p>
          )}
          {submitted && !isLoading && (results ?? []).length === 0 && (
            <Card>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Nessun possessore trovato per "{query}".
              </p>
            </Card>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(results ?? []).map((p) => (
              <PossessoreRow
                key={p.id}
                p={p}
                selected={selectedId === p.id}
                onSelect={() => setSelectedId(p.id)}
              />
            ))}
          </div>
        </div>

        {/* Detail panel */}
        <div>
          {selectedId === null ? (
            <Card title="Dettaglio possessore">
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Seleziona un possessore per visualizzare le partite associate.
              </p>
            </Card>
          ) : (
            <PossessorePanel possessoreId={selectedId} />
          )}
        </div>
      </div>
    </div>
  )
}
