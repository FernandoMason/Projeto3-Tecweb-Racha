import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import Avatar from './Avatar.jsx'
import Logo from './Logo.jsx'
import useTitulo from './useTitulo.js'

const FOCO = 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-campo-700'

/** Navbar fixa no topo + coluna central (pensado primeiro para celular). */
export function Navbar() {
  const { usuario, sair } = useAuth()
  return (
    <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex h-14 max-w-xl items-center justify-between px-4">
        <Link
          to="/grupos"
          aria-label="Racha, ir para meus grupos"
          className={`-ml-2 inline-flex h-10 items-center rounded-full px-2 ${FOCO}`}
        >
          <Logo />
        </Link>
        {usuario && (
          <div className="flex min-w-0 items-center gap-2">
            <span className="hidden max-w-48 truncate text-sm text-gray-600 sm:inline">{usuario.nome}</span>
            <Avatar nome={usuario.nome} tamanho="size-8" />
            <button
              type="button"
              onClick={sair}
              className={`-mr-2 inline-flex h-10 items-center rounded-full px-3 text-xs font-semibold text-gray-600 hover:bg-gray-100 hover:text-tinta ${FOCO}`}
            >
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

/** "← Voltar" com area de toque de 40px (o texto continua pequeno). */
export function LinkVoltar({ para, children = 'Voltar', className = '' }) {
  return (
    <Link
      to={para}
      className={`-mt-2 -ml-2 inline-flex h-10 w-fit items-center gap-1 rounded-full px-2 text-xs font-semibold text-gray-500 hover:text-tinta ${FOCO} ${className}`}
    >
      <span aria-hidden>←</span> {children}
    </Link>
  )
}

/**
 * Cabecalho de pagina com titulo, subtitulo e link de voltar opcional.
 * Tambem poe o titulo na aba do navegador ("Pelada de quinta · Racha").
 */
export function Cabecalho({ titulo, subtitulo, voltar, children }) {
  useTitulo(titulo)
  return (
    <div className="mb-6 flex flex-col gap-1">
      {voltar && <LinkVoltar para={voltar} />}
      <h1 className="text-2xl font-extrabold tracking-tight text-balance">{titulo}</h1>
      {subtitulo && <p className="text-sm text-gray-500">{subtitulo}</p>}
      {children}
    </div>
  )
}
