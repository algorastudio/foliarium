import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPartita,
  createPossessore,
  assegnaPossessore,
  createComune,
  getComuni,
  searchPossessori,
} from '../api/client'
import { Card, Button, SectionHeader } from '../components/ui'

// ── Field ─────────────────────────────────────────────────────────────────

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <label
        style={{
          display: 'block',
          fontSize: 12,
          fontWeight: 500,
          color: 'var(--text-secondary)',
          marginBottom: 4,
        }}
      >
        {label}
        {required && <span style={{ color: 'var(--coral)', marginLeft: 2 }}>*</span>}
      </label>
      {children}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  fontSize: 13,
  border: '0.5px solid var(--border)',
  borderRadius: 'var(--radius-md)',
  background: 'var(--surface)',
  color: 'var(--text)',
  outline: 'none',
}

// ── Toast ─────────────────────────────────────────────────────────────────

function Toast({ msg, ok }: { msg: string; ok: boolean }) {
  return (
    <div
      style={{
        padding: '8px 14px',
        borderRadius: 'var(--radius-md)',
        fontSize: 12,
        background: ok ? 'var(--green-light)' : 'var(--coral-light)',
        color: ok ? 'var(--green-text)' : 'var(--coral-text)',
        border: `0.5px solid ${ok ? 'rgba(15,110,86,.2)' : 'rgba(163,45,45,.2)'}`,
        marginBottom: 12,
      }}
    >
      {msg}
    </div>
  )
}

// ── Nuova Partita ─────────────────────────────────────────────────────────

function FormPartita() {
  const qc = useQueryClient()
  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })
  const [comuneId, setComuneId] = useState('')
  const [numero, setNumero] = useState('')
  const [suffisso, setSuffisso] = useState('')
  const [tipo, setTipo] = useState('Principale')
  const [stato, setStato] = useState('attiva')
  const [data, setData] = useState('')
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const mut = useMutation({
    mutationFn: createPartita,
    onSuccess: (res) => {
      setMsg({ text: `Partita creata con ID ${res.id}`, ok: true })
      setNumero(''); setSuffisso(''); setData('')
      qc.invalidateQueries({ queryKey: ['archivio-search'] })
    },
    onError: (e: Error) => setMsg({ text: e.message, ok: false }),
  })

  const handle = (e: FormEvent) => {
    e.preventDefault()
    if (!comuneId || !numero) return
    mut.mutate({
      comune_id: Number(comuneId),
      numero_partita: Number(numero),
      suffisso_partita: suffisso || undefined,
      data_impianto: data || undefined,
      tipo,
      stato,
    })
  }

  return (
    <Card title="Nuova partita catastale">
      {msg && <Toast msg={msg.text} ok={msg.ok} />}
      <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Field label="Comune" required>
            <select
              value={comuneId}
              onChange={(e) => setComuneId(e.target.value)}
              required
              style={inputStyle}
            >
              <option value="">Seleziona comune…</option>
              {(comuni ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome} ({c.provincia})
                </option>
              ))}
            </select>
          </Field>
          <Field label="Numero partita" required>
            <input
              type="number"
              value={numero}
              onChange={(e) => setNumero(e.target.value)}
              required
              min={1}
              placeholder="es. 142"
              style={inputStyle}
            />
          </Field>
          <Field label="Suffisso">
            <input
              type="text"
              value={suffisso}
              onChange={(e) => setSuffisso(e.target.value)}
              placeholder="es. bis"
              style={inputStyle}
            />
          </Field>
          <Field label="Data impianto">
            <input
              type="date"
              value={data}
              onChange={(e) => setData(e.target.value)}
              style={inputStyle}
            />
          </Field>
          <Field label="Tipo">
            <select value={tipo} onChange={(e) => setTipo(e.target.value)} style={inputStyle}>
              <option>Principale</option>
              <option>Secondaria</option>
              <option>Supplementare</option>
            </select>
          </Field>
          <Field label="Stato">
            <select value={stato} onChange={(e) => setStato(e.target.value)} style={inputStyle}>
              <option value="attiva">Attiva</option>
              <option value="chiusa">Chiusa</option>
              <option value="soppressa">Soppressa</option>
            </select>
          </Field>
        </div>
        <div>
          <Button variant="primary" type="submit" disabled={mut.isPending}>
            {mut.isPending ? 'Salvataggio…' : 'Crea partita'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

// ── Nuovo Possessore ──────────────────────────────────────────────────────

function FormPossessore() {
  const qc = useQueryClient()
  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })
  const [nomeCompleto, setNomeCompleto] = useState('')
  const [cognomeNome, setCognomeNome] = useState('')
  const [paternita, setPaternita] = useState('')
  const [comuneId, setComuneId] = useState('')
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const mut = useMutation({
    mutationFn: createPossessore,
    onSuccess: (res) => {
      setMsg({ text: `Possessore creato con ID ${res.id}`, ok: true })
      setNomeCompleto(''); setCognomeNome(''); setPaternita('')
      qc.invalidateQueries({ queryKey: ['possessori'] })
    },
    onError: (e: Error) => setMsg({ text: e.message, ok: false }),
  })

  const handle = (e: FormEvent) => {
    e.preventDefault()
    if (!nomeCompleto || !comuneId) return
    mut.mutate({
      nome_completo: nomeCompleto,
      cognome_nome: cognomeNome || undefined,
      paternita: paternita || undefined,
      comune_riferimento_id: Number(comuneId),
    })
  }

  return (
    <Card title="Nuovo possessore">
      {msg && <Toast msg={msg.text} ok={msg.ok} />}
      <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Field label="Nome completo" required>
            <input
              type="text"
              value={nomeCompleto}
              onChange={(e) => setNomeCompleto(e.target.value)}
              required
              placeholder="es. Rossi Mario"
              style={inputStyle}
            />
          </Field>
          <Field label="Cognome Nome (invertito)">
            <input
              type="text"
              value={cognomeNome}
              onChange={(e) => setCognomeNome(e.target.value)}
              placeholder="es. Rossi Mario"
              style={inputStyle}
            />
          </Field>
          <Field label="Paternità">
            <input
              type="text"
              value={paternita}
              onChange={(e) => setPaternita(e.target.value)}
              placeholder="es. fu Giovanni"
              style={inputStyle}
            />
          </Field>
          <Field label="Comune di riferimento" required>
            <select
              value={comuneId}
              onChange={(e) => setComuneId(e.target.value)}
              required
              style={inputStyle}
            >
              <option value="">Seleziona comune…</option>
              {(comuni ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome} ({c.provincia})
                </option>
              ))}
            </select>
          </Field>
        </div>
        <div>
          <Button variant="primary" type="submit" disabled={mut.isPending}>
            {mut.isPending ? 'Salvataggio…' : 'Crea possessore'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

// ── Assegna Possessore a Partita ──────────────────────────────────────────

function FormAssegna() {
  const [partitaId, setPartitaId] = useState('')
  const [query, setQuery] = useState('')
  const [selectedPoss, setSelectedPoss] = useState<{ id: number; nome_completo: string } | null>(null)
  const [titolo, setTitolo] = useState('Proprietario')
  const [quota, setQuota] = useState('')
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const { data: results } = useQuery({
    queryKey: ['possessori-search', query],
    queryFn: () => searchPossessori(query),
    enabled: query.length >= 2,
  })

  const mut = useMutation({
    mutationFn: assegnaPossessore,
    onSuccess: () => {
      setMsg({ text: 'Possessore assegnato con successo', ok: true })
      setPartitaId(''); setQuery(''); setSelectedPoss(null); setQuota('')
    },
    onError: (e: Error) => setMsg({ text: e.message, ok: false }),
  })

  const handle = (e: FormEvent) => {
    e.preventDefault()
    if (!partitaId || !selectedPoss) return
    mut.mutate({
      partita_id: Number(partitaId),
      possessore_id: selectedPoss.id,
      titolo,
      quota: quota || undefined,
    })
  }

  return (
    <Card title="Assegna possessore a partita">
      {msg && <Toast msg={msg.text} ok={msg.ok} />}
      <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Field label="ID Partita" required>
            <input
              type="number"
              value={partitaId}
              onChange={(e) => setPartitaId(e.target.value)}
              required
              min={1}
              placeholder="ID numerico partita"
              style={inputStyle}
            />
          </Field>
          <Field label="Titolo">
            <select value={titolo} onChange={(e) => setTitolo(e.target.value)} style={inputStyle}>
              <option>Proprietario</option>
              <option>Comproprietario</option>
              <option>Usufruttuario</option>
              <option>Enfiteuta</option>
            </select>
          </Field>
        </div>
        <Field label="Cerca possessore" required>
          <input
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedPoss(null) }}
            placeholder="Digita almeno 2 caratteri…"
            style={inputStyle}
          />
          {results && results.length > 0 && !selectedPoss && (
            <div
              style={{
                border: '0.5px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                marginTop: 4,
                background: 'var(--surface)',
                maxHeight: 160,
                overflowY: 'auto',
              }}
            >
              {results.slice(0, 10).map((p) => (
                <div
                  key={p.id}
                  onClick={() => { setSelectedPoss(p); setQuery(p.nome_completo) }}
                  style={{
                    padding: '6px 10px',
                    fontSize: 12,
                    cursor: 'pointer',
                    borderBottom: '0.5px solid var(--border)',
                  }}
                >
                  <span style={{ fontWeight: 500 }}>{p.nome_completo}</span>
                  {p.paternita && (
                    <span style={{ color: 'var(--text-secondary)', marginLeft: 6 }}>
                      {p.paternita}
                    </span>
                  )}
                  <span style={{ float: 'right', color: 'var(--text-secondary)' }}>
                    ID {p.id}
                  </span>
                </div>
              ))}
            </div>
          )}
          {selectedPoss && (
            <div
              style={{
                marginTop: 4,
                fontSize: 12,
                color: 'var(--purple)',
                background: 'var(--purple-light)',
                padding: '4px 8px',
                borderRadius: 4,
              }}
            >
              Selezionato: {selectedPoss.nome_completo} (ID {selectedPoss.id})
            </div>
          )}
        </Field>
        <Field label="Quota">
          <input
            type="text"
            value={quota}
            onChange={(e) => setQuota(e.target.value)}
            placeholder="es. 1/2, 2/3"
            style={{ ...inputStyle, maxWidth: 160 }}
          />
        </Field>
        <div>
          <Button
            variant="primary"
            type="submit"
            disabled={mut.isPending || !selectedPoss || !partitaId}
          >
            {mut.isPending ? 'Salvataggio…' : 'Assegna'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

// ── Nuovo Comune ──────────────────────────────────────────────────────────

function FormComune() {
  const qc = useQueryClient()
  const [nome, setNome] = useState('')
  const [provincia, setProvincia] = useState('')
  const [regione, setRegione] = useState('')
  const [codice, setCodice] = useState('')
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const mut = useMutation({
    mutationFn: createComune,
    onSuccess: (res) => {
      setMsg({ text: `Comune creato con ID ${res.id}`, ok: true })
      setNome(''); setProvincia(''); setRegione(''); setCodice('')
      qc.invalidateQueries({ queryKey: ['comuni'] })
    },
    onError: (e: Error) => setMsg({ text: e.message, ok: false }),
  })

  const handle = (e: FormEvent) => {
    e.preventDefault()
    if (!nome || !provincia || !regione) return
    mut.mutate({ nome, provincia, regione, codice_catastale: codice || undefined })
  }

  return (
    <Card title="Nuovo comune">
      {msg && <Toast msg={msg.text} ok={msg.ok} />}
      <form onSubmit={handle} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Field label="Nome" required>
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              required
              placeholder="es. Savona"
              style={inputStyle}
            />
          </Field>
          <Field label="Provincia" required>
            <input
              type="text"
              value={provincia}
              onChange={(e) => setProvincia(e.target.value.toUpperCase().slice(0, 2))}
              required
              maxLength={2}
              placeholder="es. SV"
              style={{ ...inputStyle, textTransform: 'uppercase' }}
            />
          </Field>
          <Field label="Regione" required>
            <input
              type="text"
              value={regione}
              onChange={(e) => setRegione(e.target.value)}
              required
              placeholder="es. Liguria"
              style={inputStyle}
            />
          </Field>
          <Field label="Codice catastale">
            <input
              type="text"
              value={codice}
              onChange={(e) => setCodice(e.target.value.toUpperCase().slice(0, 4))}
              maxLength={4}
              placeholder="es. I480"
              style={{ ...inputStyle, textTransform: 'uppercase' }}
            />
          </Field>
        </div>
        <div>
          <Button variant="primary" type="submit" disabled={mut.isPending}>
            {mut.isPending ? 'Salvataggio…' : 'Crea comune'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

// ── Tabs ──────────────────────────────────────────────────────────────────

const TABS = [
  { key: 'partita', label: 'Nuova partita' },
  { key: 'possessore', label: 'Nuovo possessore' },
  { key: 'assegna', label: 'Assegna possessore' },
  { key: 'comune', label: 'Nuovo comune' },
]

export default function Inserimento() {
  const [tab, setTab] = useState('partita')

  return (
    <div>
      <SectionHeader title="Inserimento dati" />
      <div
        style={{
          display: 'flex',
          gap: 4,
          marginBottom: 16,
          borderBottom: '0.5px solid var(--border)',
          paddingBottom: 0,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: '8px 14px',
              fontSize: 13,
              background: 'none',
              border: 'none',
              borderBottom: tab === t.key ? '2px solid var(--purple)' : '2px solid transparent',
              color: tab === t.key ? 'var(--text)' : 'var(--text-secondary)',
              fontWeight: tab === t.key ? 500 : 400,
              cursor: 'pointer',
              transition: 'color .15s',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'partita' && <FormPartita />}
      {tab === 'possessore' && <FormPossessore />}
      {tab === 'assegna' && <FormAssegna />}
      {tab === 'comune' && <FormComune />}
    </div>
  )
}
