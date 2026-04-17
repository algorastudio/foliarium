import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import RicercaPartite from './pages/RicercaPartite'
import Placeholder from './pages/Placeholder'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth()
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={<PrivateRoute><Layout /></PrivateRoute>}
            >
              <Route index element={<Dashboard />} />
              <Route path="partite" element={<RicercaPartite />} />
              <Route path="nuova-partita" element={<Placeholder title="Nuova Partita" />} />
              <Route path="possessori" element={<Placeholder title="Possessori" />} />
              <Route path="documenti" element={<Placeholder title="Documenti" />} />
              <Route path="statistiche" element={<Placeholder title="Statistiche" />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
