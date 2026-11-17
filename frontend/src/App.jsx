import { Navigate, Route, Routes } from 'react-router-dom'
import { RotaProtegida, RotaPublica } from './auth/Rotas.jsx'
import Layout from './components/Layout.jsx'
import Cadastro from './pages/Cadastro.jsx'
import CriarOuEntrar from './pages/CriarOuEntrar.jsx'
import Grupo from './pages/Grupo.jsx'
import Inicio from './pages/Inicio.jsx'
import Login from './pages/Login.jsx'
import MeusGrupos from './pages/MeusGrupos.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<RotaPublica />}>
        <Route path="/" element={<Inicio />} />
        <Route path="/login" element={<Login />} />
        <Route path="/cadastro" element={<Cadastro />} />
      </Route>

      <Route element={<RotaProtegida />}>
        <Route element={<Layout />}>
          <Route path="/grupos" element={<MeusGrupos />} />
          <Route path="/grupos/novo" element={<CriarOuEntrar />} />
          <Route path="/grupos/:id" element={<Grupo />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
