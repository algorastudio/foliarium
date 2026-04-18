export default function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-gray-400">
      <div className="text-4xl mb-3">🚧</div>
      <p className="font-medium text-gray-600">{title}</p>
      <p className="text-sm mt-1">Pagina in costruzione</p>
    </div>
  )
}
