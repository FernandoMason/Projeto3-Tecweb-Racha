import { Navigate, Outlet, useLocation } from 'react-router-dom'
import Carregando from '../components/Carregando.jsx'
import { useAuth } from './AuthContext.jsx'

/** So deixa passar quem esta logado; senao manda para o login e volta depois. */
export function RotaProtegida() {
  const { usuario, carregando } = useAuth()
  const location = useLocation()
  if (carregando) return <Carregando tela />
  if (!usuario) return <Navigate to="/login" replace state={{ de: location.pathname }} />
  return <Outlet />
}

/** Telas de inicio/login/cadastro: quem ja esta logado vai direto para os grupos. */
export function RotaPublica() {
  const { usuario, carregando } = useAuth()
  if (carregando) return <Carregando tela />
  if (usuario) return <Navigate to="/grupos" replace />
  return <Outlet />
}
