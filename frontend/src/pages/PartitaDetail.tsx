import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPartita } from '../api/client'
import { Card, StatusChip, MiniTag, SectionHeader } from '../components/ui'
import type { Immobile, Variazione, Possessore_PP } from '../api/client'

type Tab = 'possessori' | 'immobili' | 'variazioni'

const TAB_LABELS: Record<Tab, string> = {
  possessori: 'Possessori',
  immobili: 'Immobili',
  variazioni: 'Variazioni',
}

function StatoBadge({ stato }: { stato: string }) {
  const v = stato?.toLowerCase() === 'attiva' ? 'ok' : stato?.toLowerCase() === 'chiusa' ? 'neutral' : 'warn'
  return <StatusChip variant={v}>{stato}</StatusChip>
}

function PossessoriTab({ rows }: { rows: Possessore_PP[] }) {
  if (rows.length === 0)
    return <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessun possessore associato.</p>
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: '0.5px solid var(--border)' }}>
          {['Nome completo', 'Titolo', 'Quota'].map((h) => (
            <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500, color: 'var(--text-secondary)', fontSize: 12 }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr key={p.id} style={{ borderBottom: '0.5px solid var(--border)' }}>
            <td style={{ padding: '8px 8px', fontWeight: 500 }}>{p.nome_completo}</td>
            <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{p.titolo ?? '—'}</td>
            <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{p.quota ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ImmobiliTab({ rows }: { rows: Immobile[] }) {
  if (rows.length === 0)
    return <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessun immobile registrato.</p>
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: '0.5px solid var(--border)' }}>
          {['Località', 'Natura', 'Piani', 'Vani', 'Consistenza', 'Classe'].map((h) => (
            <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500, color: 'var(--text-secondary)', fontSize: 12 }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((im) => (
          <tr key={im.id} style={{ borderBottom: '0.5px solid var(--border)' }}>
            <td style={{ padding: '8px 8px' }}>{im.localita_nome}</td>
            <td style={{ padding: '8px 8px', fontWeight: 500 }}>{im.natura}</td>
            <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{im.numero_piani ?? '—'}</td>
            <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{im.numero_vani ?? '—'}</td>
            <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{im.consistenza ?? '—'}</td>
            <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{im.classificazione ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function VariazioniTab({ rows, partitaId }: { rows: Variazione[]; partitaId: number }) {
  const navigate = useNavigate()
  if (rows.length === 0)
    return <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessuna variazione registrata.</p>

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: '0.5px solid var(--border)' }}>
          {['Data', 'Tipo', 'Contratto', 'Notaio', 'Partita origine', 'Partita dest.'].map((h) => (
            <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500, color: 'var(--text-secondary)', fontSize: 12 }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((v) => {
          const isOrigin = v.partita_origine_id === partitaId
          return (
            <tr key={v.id} style={{ borderBottom: '0.5px solid var(--border)' }}>
              <td style={{ padding: '8px 8px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                {v.data_variazione ? v.data_variazione.slice(0, 10) : '—'}
              </td>
              <td style={{ padding: '8px 8px', fontWeight: 500 }}>{v.tipo ?? '—'}</td>
              <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{v.tipo_contratto ?? '—'}</td>
              <td style={{ padding: '8px 8px', color: 'var(--text-secondary)' }}>{v.notaio ?? '—'}</td>
              <td style={{ padding: '8px 8px' }}>
                {v.partita_origine_id ? (
                  <span
                    onClick={() => navigate(`/partite/${v.partita_origine_id}`)}
                    style={{
                      color: isOrigin ? 'var(--text-secondary)' : 'var(--purple)',
                      cursor: isOrigin ? 'default' : 'pointer',
                      textDecoration: isOrigin ? 'none' : 'underline',
                    }}
                  >
                    {v.origine_numero_partita ?? v.partita_origine_id}
                    {v.origine_comune_nome ? ` — ${v.origine_comune_nome}` : ''}
                  </span>
                ) : '—'}
              </td>
              <td style={{ padding: '8px 8px' }}>
                {v.partita_destinazione_id ? (
                  <span
                    onClick={() => navigate(`/partite/${v.partita_destinazione_id}`)}
                    style={{
                      color: !isOrigin ? 'var(--text-secondary)' : 'var(--purple)',
                      cursor: !isOrigin ? 'default' : 'pointer',
                      textDecoration: !isOrigin ? 'none' : 'underline',
                    }}
                  >
                    {v.destinazione_numero_partita ?? v.partita_destinazione_id}
                    {v.destinazione_comune_nome ? ` — ${v.destinazione_comune_nome}` : ''}
                  </span>
                ) : '—'}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export default function PartitaDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('possessori')

  const partitaId = Number(id)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['partita', partitaId],
    queryFn: () => getPartita(partitaId),
    enabled: !isNaN(partitaId),
  })

  if (isLoading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 13 }}>
        Caricamento partita…
      </div>
    )
  }

  if (isError || !data) {
    return (
      <Card>
        <p style={{ color: 'var(--coral-text)', fontSize: 13 }}>Partita non trovata o errore di caricamento.</p>
        <button
          onClick={() => navigate(-1)}
          style={{ marginTop: 12, fontSize: 12, color: 'var(--purple)', cursor: 'pointer', background: 'none', border: 'none' }}
        >
          ← Torna indietro
        </button>
      </Card>
    )
  }

  const d = data

  return (
    <div>
      {/* Header breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            fontSize: 12,
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            background: 'none',
            border: 'none',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          ← Archivio
        </button>
        <span style={{ fontSize: 12, color: 'var(--border-md)' }}>/</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Partita {d.numero_partita}{d.suffisso_partita ? `/${d.suffisso_partita}` : ''}
        </span>
      </div>

      {/* Main header card */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 20, fontWeight: 500, letterSpacing: '-0.4px' }}>
                Partita {d.numero_partita}
                {d.suffisso_partita ? `/${d.suffisso_partita}` : ''}
              </span>
              <StatoBadge stato={d.stato} />
              <MiniTag>{d.tipo}</MiniTag>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {d.comune_nome}
              {d.data_impianto && ` · Impianto: ${d.data_impianto.slice(0, 10)}`}
              {d.data_chiusura && ` · Chiusura: ${d.data_chiusura.slice(0, 10)}`}
              {d.numero_provenienza && ` · Provenienza: ${d.numero_provenienza}`}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={() => navigate(`/genealogia?partita_id=${d.id}`)}
              style={{
                fontSize: 12,
                padding: '5px 12px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--purple-light)',
                color: 'var(--purple-dark)',
                border: '0.5px solid var(--purple-border)',
                cursor: 'pointer',
              }}
            >
              Genealogia
            </button>
          </div>
        </div>

        {/* Stats pills */}
        <div style={{ display: 'flex', gap: 16, marginTop: 14, paddingTop: 12, borderTop: '0.5px solid var(--border)' }}>
          {[
            { label: 'Possessori', count: d.possessori.length },
            { label: 'Immobili', count: d.immobili.length },
            { label: 'Variazioni', count: d.variazioni.length },
          ].map(({ label, count }) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 18, fontWeight: 500 }}>{count}</span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{label}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 2, borderBottom: '0.5px solid var(--border)', marginBottom: 14 }}>
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '8px 14px',
              fontSize: 13,
              background: 'none',
              border: 'none',
              borderBottom: tab === t ? '2px solid var(--purple)' : '2px solid transparent',
              color: tab === t ? 'var(--text)' : 'var(--text-secondary)',
              fontWeight: tab === t ? 500 : 400,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {TAB_LABELS[t]}
            <span
              style={{
                fontSize: 11,
                padding: '1px 6px',
                borderRadius: 10,
                background: tab === t ? 'var(--purple-light)' : 'var(--bg-secondary)',
                color: tab === t ? 'var(--purple-dark)' : 'var(--text-secondary)',
              }}
            >
              {t === 'possessori' ? d.possessori.length : t === 'immobili' ? d.immobili.length : d.variazioni.length}
            </span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <Card>
        <SectionHeader
          title={TAB_LABELS[tab]}
          right={<MiniTag>ID partita: {d.id}</MiniTag>}
        />
        {tab === 'possessori' && <PossessoriTab rows={d.possessori} />}
        {tab === 'immobili' && <ImmobiliTab rows={d.immobili} />}
        {tab === 'variazioni' && <VariazioniTab rows={d.variazioni} partitaId={d.id} />}
      </Card>
    </div>
  )
}
