import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Archivio from './pages/Archivio'
import Genealogia from './pages/Genealogia'
import Analytics from './pages/Analytics'
import Audit from './pages/Audit'
import PartitaDetail from './pages/PartitaDetail'
import Possessori from './pages/Possessori'
import Inserimento from './pages/Inserimento'

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
              element={
                <PrivateRoute>
                  <Layout />
                </PrivateRoute>
              }
            >
              <Route index element={<Navigate to="/archivio" replace />} />
              <Route path="archivio" element={<Archivio />} />
              <Route path="partite/:id" element={<PartitaDetail />} />
              <Route path="possessori" element={<Possessori />} />
              <Route path="inserimento" element={<Inserimento />} />
              <Route path="genealogia" element={<Genealogia />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="audit" element={<Audit />} />
            </Route>
            <Route path="*" element={<Navigate to="/archivio" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
