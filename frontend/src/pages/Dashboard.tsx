import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '../api/client'
import { FileText, MapPin, TrendingUp } from 'lucide-react'

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number | string; icon: React.ElementType; color: string
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-800">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  if (isLoading) return <div className="text-gray-500 text-sm">Caricamento…</div>
  if (error) return <div className="text-red-500 text-sm">Errore: {(error as Error).message}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-800">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Panoramica dell'archivio catastale</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Partite totali"
          value={data?.totale_partite ?? 0}
          icon={FileText}
          color="bg-[#3f51b5]"
        />
        <StatCard
          label="Comuni registrati"
          value={data?.totale_comuni ?? 0}
          icon={MapPin}
          color="bg-[#00897b]"
        />
        <StatCard
          label="Media partite/comune"
          value={data && data.totale_comuni > 0
            ? (data.totale_partite / data.totale_comuni).toFixed(1)
            : '—'}
          icon={TrendingUp}
          color="bg-[#f57c00]"
        />
      </div>

      {/* Top comuni */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">Comuni per numero di partite</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 text-xs border-b border-gray-100">
              <th className="px-5 py-2.5 font-medium">Comune</th>
              <th className="px-5 py-2.5 font-medium text-right">Partite</th>
            </tr>
          </thead>
          <tbody>
            {(data?.per_comune ?? []).map((row, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                <td className="px-5 py-2.5">{row.comune_nome ?? row.nome ?? '—'}</td>
                <td className="px-5 py-2.5 text-right font-medium text-[#3f51b5]">
                  {row.num_partite}
                </td>
              </tr>
            ))}
            {(!data?.per_comune?.length) && (
              <tr>
                <td colSpan={2} className="px-5 py-4 text-center text-gray-400">Nessun dato</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
