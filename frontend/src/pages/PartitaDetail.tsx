import { useState, type FormEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPartita, addImmobile, deleteImmobile, addVariazione, deleteVariazione,
  type Immobile, type Variazione, type Possessore_PP,
  type AddImmobilePayload, type AddVariazionePayload,
} from '../api/client'
import { Card, StatusChip, MiniTag, SectionHeader, Button } from '../components/ui'

type Tab = 'possessori' | 'immobili' | 'variazioni'

const TAB_LABELS: Record<Tab, string> = {
  possessori: 'Possessori',
  immobili: 'Immobili',
  variazioni: 'Variazioni',
}

const TIPI_VARIAZIONE = ['Vendita', 'Acquisto', 'Successione', 'Variazione',
  'Frazionamento', 'Divisione', 'Trasferimento', 'Altro'] as const

function StatoBadge({ stato }: { stato: string }) {
  const v = stato?.toLowerCase() === 'attiva' ? 'ok' : stato?.toLowerCase() === 'chiusa' ? 'neutral' : 'warn'
  return <StatusChip variant={v}>{stato}</StatusChip>
}

// ── Possessori tab ─────────────────────────────────────────────────────────

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

// ── Immobili tab ───────────────────────────────────────────────────────────

function AddImmobileForm({
  partitaId,
  onSuccess,
}: {
  partitaId: number
  onSuccess: () => void
}) {
  const [open, setOpen] = useState(false)
  const [localita, setLocalita] = useState('')
  const [tipologia, setTipologia] = useState('')
  const [natura, setNatura] = useState('')
  const [piani, setPiani] = useState('')
  const [vani, setVani] = useState('')
  const [consistenza, setConsistenza] = useState('')
  const [classificazione, setClassificazione] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (p: AddImmobilePayload) => addImmobile(partitaId, p),
    onSuccess: () => {
      setOpen(false)
      setLocalita(''); setTipologia(''); setNatura(''); setPiani(''); setVani('')
      setConsistenza(''); setClassificazione(''); setError(null)
      onSuccess()
    },
    onError: (e: Error) => setError(e.message),
  })

  const fs = {
    padding: '6px 9px',
    border: '0.5px solid var(--border-md)',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    background: 'var(--surface)',
    color: 'var(--text)',
    width: '100%',
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!natura.trim()) return setError('Natura obbligatoria.')
    if (!localita.trim()) return setError('Località obbligatoria.')
    mutation.mutate({
      localita_nome: localita.trim(),
      tipologia_stradale: tipologia || undefined,
      natura: natura.trim(),
      numero_piani: piani ? Number(piani) : undefined,
      numero_vani: vani ? Number(vani) : undefined,
      consistenza: consistenza || undefined,
      classificazione: classificazione || undefined,
    })
  }

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} style={{ marginTop: 10 }}>+ Aggiungi immobile</Button>
    )
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: 14, padding: 14, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '0.5px solid var(--border)' }}>
      <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 10 }}>Nuovo immobile</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Località *</label>
          <input style={fs} value={localita} onChange={(e) => setLocalita(e.target.value)} placeholder="es. Via Roma 5" />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Tipologia stradale</label>
          <input style={fs} value={tipologia} onChange={(e) => setTipologia(e.target.value)} placeholder="es. Via, Piazza…" />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Natura *</label>
          <input style={fs} value={natura} onChange={(e) => setNatura(e.target.value)} placeholder="es. Fabbricato, Terreno…" />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Classificazione</label>
          <input style={fs} value={classificazione} onChange={(e) => setClassificazione(e.target.value)} placeholder="es. A/2" />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Piani</label>
          <input type="number" style={fs} value={piani} onChange={(e) => setPiani(e.target.value)} min={0} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Vani</label>
          <input type="number" style={fs} value={vani} onChange={(e) => setVani(e.target.value)} min={0} />
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Consistenza</label>
          <input style={fs} value={consistenza} onChange={(e) => setConsistenza(e.target.value)} placeholder="es. 120 mq" />
        </div>
      </div>
      {error && <div style={{ fontSize: 12, color: 'var(--coral-text)', marginBottom: 8 }}>{error}</div>}
      <div style={{ display: 'flex', gap: 8 }}>
        <Button variant="primary" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Salvataggio…' : 'Aggiungi'}
        </Button>
        <Button onClick={() => { setOpen(false); setError(null) }}>Annulla</Button>
      </div>
    </form>
  )
}

function ImmobiliTab({ rows, partitaId, onRefresh }: { rows: Immobile[]; partitaId: number; onRefresh: () => void }) {
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteImmobile(partitaId, id),
    onSuccess: onRefresh,
  })

  return (
    <div>
      {rows.length === 0 ? (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessun immobile registrato.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid var(--border)' }}>
              {['Località', 'Natura', 'Piani', 'Vani', 'Consistenza', 'Classe', ''].map((h) => (
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
                <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                  <button
                    onClick={() => deleteMutation.mutate(im.id)}
                    disabled={deleteMutation.isPending}
                    style={{ fontSize: 11, color: 'var(--coral-text)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}
                  >
                    Rimuovi
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <AddImmobileForm partitaId={partitaId} onSuccess={onRefresh} />
    </div>
  )
}

// ── Variazioni tab ─────────────────────────────────────────────────────────

function AddVariazioneForm({
  partitaId,
  onSuccess,
}: {
  partitaId: number
  onSuccess: () => void
}) {
  const [open, setOpen] = useState(false)
  const [tipo, setTipo] = useState<string>('Vendita')
  const [data, setData] = useState('')
  const [destId, setDestId] = useState('')
  const [riferimento, setRiferimento] = useState('')
  const [nominativo, setNominativo] = useState('')
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: (p: AddVariazionePayload) => addVariazione(partitaId, p),
    onSuccess: () => {
      setOpen(false)
      setTipo('Vendita'); setData(''); setDestId(''); setRiferimento(''); setNominativo('')
      setError(null)
      onSuccess()
    },
    onError: (e: Error) => setError(e.message),
  })

  const fs = {
    padding: '6px 9px',
    border: '0.5px solid var(--border-md)',
    borderRadius: 'var(--radius-md)',
    fontSize: 13,
    background: 'var(--surface)',
    color: 'var(--text)',
    width: '100%',
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!data) return setError('Data variazione obbligatoria.')
    mutation.mutate({
      tipo,
      data_variazione: data,
      partita_destinazione_id: destId ? Number(destId) : undefined,
      numero_riferimento: riferimento || undefined,
      nominativo_riferimento: nominativo || undefined,
    })
  }

  if (!open) {
    return (
      <Button onClick={() => setOpen(true)} style={{ marginTop: 10 }}>+ Registra variazione</Button>
    )
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginTop: 14, padding: 14, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', border: '0.5px solid var(--border)' }}>
      <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 10 }}>Nuova variazione</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Tipo *</label>
          <select style={fs} value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {TIPI_VARIAZIONE.map((t) => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Data *</label>
          <input type="date" style={fs} value={data} onChange={(e) => setData(e.target.value)} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>ID partita destinazione</label>
          <input type="number" style={fs} value={destId} onChange={(e) => setDestId(e.target.value)} placeholder="opzionale" />
        </div>
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Numero riferimento</label>
          <input style={fs} value={riferimento} onChange={(e) => setRiferimento(e.target.value)} placeholder="es. Rep. 1234" />
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>Nominativo di riferimento</label>
          <input style={fs} value={nominativo} onChange={(e) => setNominativo(e.target.value)} placeholder="es. Rossi Mario fu Giovanni" />
        </div>
      </div>
      {error && <div style={{ fontSize: 12, color: 'var(--coral-text)', marginBottom: 8 }}>{error}</div>}
      <div style={{ display: 'flex', gap: 8 }}>
        <Button variant="primary" type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Salvataggio…' : 'Registra'}
        </Button>
        <Button onClick={() => { setOpen(false); setError(null) }}>Annulla</Button>
      </div>
    </form>
  )
}

function VariazioniTab({
  rows,
  partitaId,
  onRefresh,
}: {
  rows: Variazione[]
  partitaId: number
  onRefresh: () => void
}) {
  const navigate = useNavigate()
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteVariazione(partitaId, id),
    onSuccess: onRefresh,
  })

  return (
    <div>
      {rows.length === 0 ? (
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Nessuna variazione registrata.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid var(--border)' }}>
              {['Data', 'Tipo', 'Contratto', 'Notaio', 'Partita origine', 'Partita dest.', ''].map((h) => (
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
                        onClick={() => !isOrigin && navigate(`/partite/${v.partita_origine_id}`)}
                        style={{ color: isOrigin ? 'var(--text-secondary)' : 'var(--purple)', cursor: isOrigin ? 'default' : 'pointer', textDecoration: isOrigin ? 'none' : 'underline' }}
                      >
                        {v.origine_numero_partita ?? v.partita_origine_id}
                        {v.origine_comune_nome ? ` — ${v.origine_comune_nome}` : ''}
                      </span>
                    ) : '—'}
                  </td>
                  <td style={{ padding: '8px 8px' }}>
                    {v.partita_destinazione_id ? (
                      <span
                        onClick={() => isOrigin && navigate(`/partite/${v.partita_destinazione_id}`)}
                        style={{ color: !isOrigin ? 'var(--text-secondary)' : 'var(--purple)', cursor: !isOrigin ? 'default' : 'pointer', textDecoration: !isOrigin ? 'none' : 'underline' }}
                      >
                        {v.destinazione_numero_partita ?? v.partita_destinazione_id}
                        {v.destinazione_comune_nome ? ` — ${v.destinazione_comune_nome}` : ''}
                      </span>
                    ) : '—'}
                  </td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>
                    <button
                      onClick={() => deleteMutation.mutate(v.id)}
                      disabled={deleteMutation.isPending}
                      style={{ fontSize: 11, color: 'var(--coral-text)', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}
                    >
                      Rimuovi
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
      <AddVariazioneForm partitaId={partitaId} onSuccess={onRefresh} />
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function PartitaDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('possessori')

  const partitaId = Number(id)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['partita', partitaId],
    queryFn: () => getPartita(partitaId),
    enabled: !isNaN(partitaId),
  })

  const refresh = () => qc.invalidateQueries({ queryKey: ['partita', partitaId] })

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
      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <button
          onClick={() => navigate(-1)}
          style={{ fontSize: 12, color: 'var(--text-secondary)', cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}
        >
          ← Archivio
        </button>
        <span style={{ fontSize: 12, color: 'var(--border-md)' }}>/</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Partita {d.numero_partita}{d.suffisso_partita ? `/${d.suffisso_partita}` : ''}
        </span>
      </div>

      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 20, fontWeight: 500, letterSpacing: '-0.4px' }}>
                Partita {d.numero_partita}{d.suffisso_partita ? `/${d.suffisso_partita}` : ''}
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
          <button
            onClick={() => navigate(`/genealogia?partita_id=${d.id}`)}
            style={{
              fontSize: 12, padding: '5px 12px', borderRadius: 'var(--radius-md)',
              background: 'var(--purple-light)', color: 'var(--purple-dark)',
              border: '0.5px solid var(--purple-border)', cursor: 'pointer',
            }}
          >
            Genealogia
          </button>
        </div>

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
              padding: '8px 14px', fontSize: 13, background: 'none', border: 'none',
              borderBottom: tab === t ? '2px solid var(--purple)' : '2px solid transparent',
              color: tab === t ? 'var(--text)' : 'var(--text-secondary)',
              fontWeight: tab === t ? 500 : 400, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {TAB_LABELS[t]}
            <span style={{
              fontSize: 11, padding: '1px 6px', borderRadius: 10,
              background: tab === t ? 'var(--purple-light)' : 'var(--bg-secondary)',
              color: tab === t ? 'var(--purple-dark)' : 'var(--text-secondary)',
            }}>
              {t === 'possessori' ? d.possessori.length : t === 'immobili' ? d.immobili.length : d.variazioni.length}
            </span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <Card>
        <SectionHeader title={TAB_LABELS[tab]} right={<MiniTag>ID partita: {d.id}</MiniTag>} />
        {tab === 'possessori' && <PossessoriTab rows={d.possessori} />}
        {tab === 'immobili' && <ImmobiliTab rows={d.immobili} partitaId={d.id} onRefresh={refresh} />}
        {tab === 'variazioni' && <VariazioniTab rows={d.variazioni} partitaId={d.id} onRefresh={refresh} />}
      </Card>
    </div>
  )
}
