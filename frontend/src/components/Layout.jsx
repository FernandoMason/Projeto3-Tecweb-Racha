import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import Avatar from './Avatar.jsx'
import Logo from './Logo.jsx'

/** Navbar fixa no topo + coluna central (pensado primeiro para celular). */
export function Navbar() {
  const { usuario, sair } = useAuth()
  return (
    <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-xl items-center justify-between px-4">
        <Link to="/grupos" aria-label="Racha, ir para meus grupos">
          <Logo />
        </Link>
        {usuario && (
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-gray-600 sm:inline">{usuario.nome}</span>
            <Avatar nome={usuario.nome} tamanho="size-8" />
            <button onClick={sair} className="rounded-full px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-100">
              Sair
            </button>
          </div>
        )}
      </nav>
    </header>
  )
}

export default function Layout() {
  return (
    <div className="min-h-dvh">
      <Navbar />
      <main className="mx-auto max-w-xl px-4 pt-6 pb-16">
        <Outlet />
      </main>
    </div>
  )
}

/** Cabecalho de pagina com titulo, subtitulo e link de voltar opcional. */
export function Cabecalho({ titulo, subtitulo, voltar, children }) {
  return (
    <div className="mb-6 flex flex-col gap-1">
      {voltar && (
        <Link to={voltar} className="mb-2 w-fit text-xs font-semibold text-gray-500 hover:text-tinta">
          ← Voltar
        </Link>
      )}
      <h1 className="text-2xl font-extrabold tracking-tight text-balance">{titulo}</h1>
      {subtitulo && <p className="text-sm text-gray-500">{subtitulo}</p>}
      {children}
    </div>
  )
}
