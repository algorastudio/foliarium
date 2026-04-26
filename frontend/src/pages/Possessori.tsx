import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { searchPossessori, getPossessore, type Possessore } from '../api/client'
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

export default function Possessori() {
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: results, isLoading } = useQuery({
    queryKey: ['possessori-search', query],
    queryFn: () => searchPossessori(query),
    enabled: submitted && query.length >= 2,
  })

  const handleSearch = () => {
    if (query.length >= 2) setSubmitted(true)
  }

  return (
    <div>
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
