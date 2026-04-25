import { useQuery } from '@tanstack/react-query'
import { getAnalytics } from '../api/client'
import { Card, Metric, BarRow, TwoCol } from '../components/ui'

const BAR_COLORS = [
  'var(--purple)',
  'var(--purple)',
  'var(--amber)',
  'var(--green)',
  'var(--coral)',
]

const DOC_COLORS: Record<string, string> = {
  Partite: 'var(--purple)',
  Variazioni: 'var(--amber)',
  'Atti notarili': 'var(--green)',
}

export default function Analytics() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['analytics'],
    queryFn: getAnalytics,
  })

  if (isLoading) {
    return (
      <Card>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Caricamento…</p>
      </Card>
    )
  }
  if (error) {
    return (
      <Card>
        <p style={{ fontSize: 12, color: 'var(--coral-text)' }}>
          Errore: {(error as Error).message}
        </p>
      </Card>
    )
  }

  const kpi = data?.kpi
  const top = data?.top_comuni ?? []
  const dist = data?.distribuzione_documenti ?? []
  const qd = data?.qualita_dati

  const maxComuni = top.reduce((m, r) => Math.max(m, r.num_partite), 0) || 1

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
        <Metric
          label="Partite catastali"
          value={kpi?.partite?.toLocaleString('it-IT') ?? '0'}
          sub="Totale archivio"
        />
        <Metric
          label="Particelle / immobili"
          value={kpi?.particelle?.toLocaleString('it-IT') ?? '0'}
          sub="Savona e provincia"
        />
        <Metric
          label="Variazioni"
          value={kpi?.variazioni?.toLocaleString('it-IT') ?? '0'}
          sub="Tutte le epoche"
        />
        <Metric
          label="Utenti attivi"
          value={kpi?.utenti_attivi?.toLocaleString('it-IT') ?? '0'}
          sub="Utenze registrate"
        />
      </div>

      <TwoCol>
        <Card title="Top comuni — partite registrate">
          {top.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Nessun dato disponibile.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {top.map((r, i) => (
                <BarRow
                  key={r.comune}
                  label={r.comune}
                  value={r.num_partite.toLocaleString('it-IT')}
                  pct={(r.num_partite / maxComuni) * 100}
                  color={BAR_COLORS[i] ?? 'var(--purple)'}
                />
              ))}
            </div>
          )}
        </Card>

        <div>
          <Card title="Distribuzione tipologia documenti">
            {dist.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Nessun dato disponibile.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {dist.map((d) => (
                  <BarRow
                    key={d.label}
                    label={d.label}
                    value={`${d.pct}%`}
                    pct={d.pct}
                    color={DOC_COLORS[d.label] ?? 'var(--purple)'}
                    labelMinWidth={88}
                  />
                ))}
              </div>
            )}
          </Card>

          <Card title="Qualità dati">
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Metric
                label="Completezza"
                value={`${qd?.completezza_pct ?? 0}%`}
                valueColor="var(--green-text)"
                style={{ minWidth: 80 }}
              />
              <Metric
                label="Duplicati"
                value={`${qd?.duplicati_pct ?? 0}%`}
                valueColor="var(--amber-text)"
                style={{ minWidth: 80 }}
              />
            </div>
          </Card>
        </div>
      </TwoCol>
    </div>
  )
}
