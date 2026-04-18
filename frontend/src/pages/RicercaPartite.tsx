import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, X, ChevronRight } from 'lucide-react'
import { searchPartite, getComuni, type Partita } from '../api/client'

const STATO_STYLE: Record<string, string> = {
  attiva:   'bg-green-100 text-green-700',
  inattiva: 'bg-gray-100 text-gray-600',
  aperta:   'bg-blue-100 text-blue-700',
  chiusa:   'bg-red-100 text-red-600',
}

function StatoBadge({ stato }: { stato: string }) {
  const cls = STATO_STYLE[stato?.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {stato}
    </span>
  )
}

function PartitaCard({ p, selected, onClick }: { p: Partita; selected: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 border rounded-xl transition-all ${
        selected
          ? 'border-[#3f51b5] bg-indigo-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-indigo-200 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-800 text-sm">
            N. {p.numero_partita}{p.suffisso_partita ? `/${p.suffisso_partita}` : ''}
          </p>
          <p className="text-xs text-gray-500 mt-0.5 truncate">{p.comune_nome}</p>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          <StatoBadge stato={p.stato} />
          <span className="text-[10px] text-gray-400">{p.tipo}</span>
        </div>
      </div>
    </button>
  )
}

function DetailPanel({ partita }: { partita: Partita }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 h-full">
      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <ChevronRight size={16} className="text-[#3f51b5]" />
        Partita N. {partita.numero_partita}
        {partita.suffisso_partita && `/${partita.suffisso_partita}`}
      </h3>
      <dl className="space-y-3 text-sm">
        {[
          ['ID', partita.id],
          ['Comune', partita.comune_nome],
          ['Tipo', partita.tipo],
          ['Stato', <StatoBadge stato={partita.stato} />],
        ].map(([label, val]) => (
          <div key={String(label)} className="flex gap-3">
            <dt className="w-28 text-gray-500 flex-shrink-0">{label}</dt>
            <dd className="text-gray-800 font-medium">{val as React.ReactNode}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export default function RicercaPartite() {
  const [params, setParams] = useState({ comune_id: undefined as number | undefined, numero_partita: undefined as number | undefined, possessore: '', immobile_natura: '' })
  const [submitted, setSubmitted] = useState(false)
  const [selected, setSelected] = useState<Partita | null>(null)
  const [statoFilter, setStatoFilter] = useState<string>('tutte')

  const { data: comuni } = useQuery({ queryKey: ['comuni'], queryFn: getComuni })
  const { data: results, isLoading } = useQuery({
    queryKey: ['partite-search', params],
    queryFn: () => searchPartite(params),
    enabled: submitted,
  })

  const filtered = (results ?? []).filter(p =>
    statoFilter === 'tutte' || p.stato?.toLowerCase() === statoFilter
  )

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    setSelected(null)
  }

  const handleClear = () => {
    setParams({ comune_id: undefined, numero_partita: undefined, possessore: '', immobile_natura: '' })
    setSubmitted(false)
    setSelected(null)
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-800">Ricerca Partite</h1>
        <p className="text-sm text-gray-500 mt-0.5">Cerca per comune, numero, possessore o natura immobile</p>
      </div>

      {/* Form ricerca */}
      <form onSubmit={handleSearch} className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Comune</label>
            <select
              value={params.comune_id ?? ''}
              onChange={e => setParams(p => ({ ...p, comune_id: e.target.value ? Number(e.target.value) : undefined }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#3f51b5]"
            >
              <option value="">— Tutti i comuni —</option>
              {(comuni ?? []).map(c => <option key={c.id} value={c.id}>{c.nome} ({c.provincia})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Numero partita</label>
            <input
              type="number"
              min={1}
              value={params.numero_partita ?? ''}
              onChange={e => setParams(p => ({ ...p, numero_partita: e.target.value ? Number(e.target.value) : undefined }))}
              placeholder="es. 1234"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#3f51b5]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Possessore</label>
            <input
              type="text"
              value={params.possessore}
              onChange={e => setParams(p => ({ ...p, possessore: e.target.value }))}
              placeholder="Nome o cognome"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#3f51b5]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Natura immobile</label>
            <input
              type="text"
              value={params.immobile_natura}
              onChange={e => setParams(p => ({ ...p, immobile_natura: e.target.value }))}
              placeholder="es. Casa, Prato…"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#3f51b5]"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="flex items-center gap-2 bg-[#3f51b5] hover:bg-[#303f9f] text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Search size={14} /> Cerca
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg text-sm border border-gray-200 hover:border-gray-300 transition-colors"
          >
            <X size={14} /> Pulisci
          </button>
        </div>
      </form>

      {/* Risultati */}
      {submitted && (
        <div>
          {/* Filter chips */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-gray-500">{filtered.length} risultati</span>
            <div className="flex gap-1 ml-auto">
              {['tutte', 'attiva', 'inattiva'].map(s => (
                <button
                  key={s}
                  onClick={() => setStatoFilter(s)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                    statoFilter === s
                      ? 'bg-[#3f51b5] text-white border-[#3f51b5]'
                      : 'text-gray-600 border-gray-200 hover:border-[#3f51b5] hover:text-[#3f51b5]'
                  }`}
                >
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-4 items-start">
            {/* Card list */}
            <div className="flex-1 min-w-0 space-y-2 max-h-[calc(100vh-340px)] overflow-y-auto pr-1">
              {isLoading && <p className="text-sm text-gray-500">Ricerca in corso…</p>}
              {!isLoading && filtered.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-8">Nessuna partita trovata</p>
              )}
              {filtered.map(p => (
                <PartitaCard
                  key={p.id}
                  p={p}
                  selected={selected?.id === p.id}
                  onClick={() => setSelected(selected?.id === p.id ? null : p)}
                />
              ))}
            </div>

            {/* Detail panel */}
            {selected && (
              <div className="w-72 flex-shrink-0">
                <DetailPanel partita={selected} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
