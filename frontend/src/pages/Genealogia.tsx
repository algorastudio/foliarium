import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getGenealogia,
  searchPartite,
  type GenealogiaNode,
  type Partita,
} from '../api/client'
import { Card, Button, TwoCol } from '../components/ui'

function NodeBox({
  node,
  highlight,
  label,
}: {
  node: GenealogiaNode
  highlight?: boolean
  label?: string
}) {
  return (
    <div
      style={{
        background: highlight ? 'var(--purple-light)' : 'var(--surface)',
        border: highlight
          ? '0.5px solid var(--purple)'
          : '0.5px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '8px 14px',
        textAlign: 'center',
        minWidth: 140,
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)' }}>
        Partita {node.numero_partita}
        {node.suffisso_partita ? `/${node.suffisso_partita}` : ''}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
        {label ?? node.comune_nome}
      </div>
      {node.possessori && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--text-secondary)',
            marginTop: 4,
            maxWidth: 180,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {node.possessori}
        </div>
      )}
    </div>
  )
}

function NodeLine() {
  return <div style={{ width: 1, height: 16, background: 'var(--border)', margin: '0 auto' }} />
}

export default function Genealogia() {
  const [searchTerm, setSearchTerm] = useState('')
  const [searchedPartiteId, setSearchedPartiteId] = useState<number | null>(null)

  const { data: partiteResults, isLoading: partLoading } = useQuery({
    queryKey: ['genealogia-search-partite', searchTerm],
    queryFn: () =>
      searchPartite({
        possessore: /^\d+$/.test(searchTerm) ? undefined : searchTerm,
        numero_partita: /^\d+$/.test(searchTerm) ? Number(searchTerm) : undefined,
      }),
    enabled: searchTerm.length >= 2,
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['genealogia', searchedPartiteId],
    queryFn: () => getGenealogia(searchedPartiteId!),
    enabled: searchedPartiteId !== null,
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (partiteResults && partiteResults.length > 0) {
      setSearchedPartiteId(partiteResults[0].id)
    }
  }

  const total = data
    ? (data.predecessori.length + data.successori.length + (data.partita ? 1 : 0))
    : 0

  return (
    <div>
      <form
        onSubmit={handleSubmit}
        style={{ display: 'flex', gap: 8, marginBottom: 14 }}
      >
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Cerca partita per numero o possessore…"
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
        <Button
          type="submit"
          variant="primary"
          disabled={!partiteResults || partiteResults.length === 0}
        >
          Mostra albero
        </Button>
      </form>

      {/* Pick from results */}
      {searchTerm.length >= 2 && partiteResults && partiteResults.length > 0 && (
        <Card style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
            {partLoading ? 'Caricamento…' : `${partiteResults.length} partite trovate — seleziona`}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {partiteResults.slice(0, 12).map((p: Partita) => (
              <button
                key={p.id}
                onClick={() => setSearchedPartiteId(p.id)}
                style={{
                  padding: '4px 10px',
                  fontSize: 12,
                  borderRadius: 'var(--radius-md)',
                  background:
                    p.id === searchedPartiteId
                      ? 'var(--purple-light)'
                      : 'var(--surface)',
                  border:
                    p.id === searchedPartiteId
                      ? '0.5px solid var(--purple)'
                      : '0.5px solid var(--border)',
                  color: p.id === searchedPartiteId ? 'var(--purple-dark)' : 'var(--text)',
                  cursor: 'pointer',
                }}
              >
                {p.numero_partita}
                {p.suffisso_partita ? `/${p.suffisso_partita}` : ''} · {p.comune_nome}
              </button>
            ))}
          </div>
        </Card>
      )}

      {!searchedPartiteId && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Cerca una partita per visualizzarne l'albero genealogico (predecessori e successori).
          </p>
        </Card>
      )}

      {searchedPartiteId && isLoading && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Caricamento albero…</p>
        </Card>
      )}

      {error && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--coral-text)' }}>
            {(error as Error).message}
          </p>
        </Card>
      )}

      {data && data.partita && (
        <TwoCol>
          <Card title={`Albero genealogico — Partita ${data.partita.numero_partita}`}>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 0,
                padding: '8px 0',
              }}
            >
              {data.predecessori.length > 0 && (
                <>
                  <div
                    style={{
                      display: 'flex',
                      gap: 16,
                      flexWrap: 'wrap',
                      justifyContent: 'center',
                    }}
                  >
                    {data.predecessori.map((n) => (
                      <NodeBox
                        key={`pred-${n.id}`}
                        node={n}
                        label={n.tipo_variazione || 'Predecessore'}
                      />
                    ))}
                  </div>
                  <NodeLine />
                </>
              )}

              <NodeBox node={data.partita} highlight label="Partita corrente" />

              {data.successori.length > 0 && (
                <>
                  <NodeLine />
                  <div
                    style={{
                      display: 'flex',
                      gap: 16,
                      flexWrap: 'wrap',
                      justifyContent: 'center',
                    }}
                  >
                    {data.successori.map((n) => (
                      <NodeBox
                        key={`succ-${n.id}`}
                        node={n}
                        label={n.tipo_variazione || 'Successore'}
                      />
                    ))}
                  </div>
                </>
              )}
            </div>
          </Card>

          <div>
            <Card title="Proprietà associate">
              {data.partita.possessori ? (
                <div style={{ fontSize: 12, color: 'var(--text)' }}>
                  {data.partita.possessori.split(',').map((p, i) => (
                    <div
                      key={i}
                      style={{
                        padding: '6px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      {p.trim()}
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  Nessun possessore registrato.
                </p>
              )}
            </Card>

            <Card title="Riepilogo genealogico">
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <tbody>
                  <tr>
                    <td
                      style={{
                        color: 'var(--text-secondary)',
                        padding: '5px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      Predecessori
                    </td>
                    <td
                      style={{
                        textAlign: 'right',
                        fontWeight: 500,
                        padding: '5px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      {data.predecessori.length}
                    </td>
                  </tr>
                  <tr>
                    <td
                      style={{
                        color: 'var(--text-secondary)',
                        padding: '5px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      Successori
                    </td>
                    <td
                      style={{
                        textAlign: 'right',
                        fontWeight: 500,
                        padding: '5px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      {data.successori.length}
                    </td>
                  </tr>
                  <tr>
                    <td
                      style={{
                        color: 'var(--text-secondary)',
                        padding: '5px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      Stato
                    </td>
                    <td
                      style={{
                        textAlign: 'right',
                        fontWeight: 500,
                        padding: '5px 0',
                        borderBottom: '0.5px solid var(--border)',
                      }}
                    >
                      {data.partita.stato}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)', padding: '5px 0' }}>
                      Nodi totali
                    </td>
                    <td style={{ textAlign: 'right', fontWeight: 500, padding: '5px 0' }}>
                      {total}
                    </td>
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>
        </TwoCol>
      )}
    </div>
  )
}
