import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAuditLog, getAuditSummary, type AuditEntry } from '../api/client'
import {
  Card,
  Metric,
  FilterChip,
  StatusChip,
  SectionHeader,
  Button,
} from '../components/ui'

const FILTERS: Array<{ key: string; label: string; op?: string }> = [
  { key: 'tutti', label: 'Tutti' },
  { key: 'view', label: 'Consultazioni', op: 'S' },
  { key: 'edit', label: 'Modifiche', op: 'U' },
  { key: 'insert', label: 'Inserimenti', op: 'I' },
  { key: 'delete', label: 'Eliminazioni', op: 'D' },
]

function operationIcon(op: string | null): {
  bg: string
  fg: string
  symbol: string
} {
  switch (op) {
    case 'I':
      return { bg: 'var(--green-light)', fg: 'var(--green-text)', symbol: '+' }
    case 'U':
      return { bg: 'var(--amber-light)', fg: 'var(--amber-text)', symbol: '✎' }
    case 'D':
      return { bg: 'var(--coral-light)', fg: 'var(--coral-text)', symbol: '✕' }
    case 'S':
      return { bg: 'var(--info-light)', fg: 'var(--info-text)', symbol: '👁' }
    default:
      return { bg: 'var(--bg-secondary)', fg: 'var(--text-secondary)', symbol: '·' }
  }
}

function fmtTime(ts: string | null): string {
  if (!ts) return ''
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
}

function fmtDate(ts: string | null): string {
  if (!ts) return ''
  const date = new Date(ts)
  if (Number.isNaN(date.getTime())) return ts
  return date.toLocaleDateString('it-IT', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

function exportCsv(entries: AuditEntry[]) {
  const header = ['timestamp', 'username', 'tabella', 'operazione', 'record_id', 'dettagli']
  const lines = [header.join(';')]
  for (const e of entries) {
    const row = [
      e.timestamp ?? '',
      e.username ?? '',
      e.tabella ?? '',
      e.operazione ?? '',
      e.record_id?.toString() ?? '',
      (e.dettagli ?? '').replace(/[\r\n;]/g, ' '),
    ]
    lines.push(row.map((c) => `"${c.replace(/"/g, '""')}"`).join(';'))
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `audit_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function Audit() {
  const [filter, setFilter] = useState<string>('tutti')

  const { data: summary } = useQuery({
    queryKey: ['audit-summary'],
    queryFn: getAuditSummary,
  })
  const op = FILTERS.find((f) => f.key === filter)?.op
  const { data: log, isLoading } = useQuery({
    queryKey: ['audit-log', filter],
    queryFn: () => getAuditLog({ operation: op, page: 1, page_size: 100 }),
  })

  const items = log?.items ?? []

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
        <Metric label="Azioni oggi" value={summary?.azioni_oggi ?? 0} />
        <Metric label="Utenti attivi" value={summary?.utenti_attivi ?? 0} />
        <Metric label="Export effettuati" value={summary?.export_effettuati ?? 0} />
        <Metric
          label="Anomalie"
          value={summary?.anomalie ?? 0}
          valueColor={summary?.anomalie ? 'var(--coral-text)' : undefined}
        />
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        {FILTERS.map((f) => (
          <FilterChip
            key={f.key}
            active={filter === f.key}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </FilterChip>
        ))}
      </div>

      <SectionHeader
        title={`Registro attività — ${fmtDate(new Date().toISOString())}`}
        right={
          <Button onClick={() => exportCsv(items)} style={{ fontSize: 12, padding: '5px 10px' }}>
            Esporta CSV
          </Button>
        }
      />

      {isLoading && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Caricamento log…</p>
        </Card>
      )}

      {!isLoading && items.length === 0 && (
        <Card>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Nessuna voce di audit per il filtro selezionato.
          </p>
        </Card>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.map((e) => {
          const ic = operationIcon(e.operazione)
          const isAnomaly = e.operazione === 'D'
          return (
            <div
              key={e.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 14px',
                background: 'var(--surface)',
                borderRadius: 'var(--radius-md)',
                border: '0.5px solid var(--border)',
              }}
            >
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 6,
                  background: ic.bg,
                  color: ic.fg,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  fontSize: 13,
                }}
              >
                {ic.symbol}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'var(--text)' }}>
                  {(e.operazione_label || 'Operazione').replace(/^\w/, (c) => c.toUpperCase())}{' '}
                  — {e.tabella || '—'}{' '}
                  {e.record_id != null && (
                    <span style={{ color: 'var(--text-secondary)' }}>
                      · ID {e.record_id}
                    </span>
                  )}{' '}
                  {isAnomaly ? (
                    <StatusChip variant="error">Anomalia</StatusChip>
                  ) : (
                    <StatusChip variant="ok">OK</StatusChip>
                  )}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {e.username || 'sistema'}
                  {e.client_ip ? ` · IP ${e.client_ip}` : ''}
                </div>
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--text-secondary)',
                  whiteSpace: 'nowrap',
                }}
              >
                {fmtTime(e.timestamp)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
