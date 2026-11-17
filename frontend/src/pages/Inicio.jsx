import Botao from '../components/Botao.jsx'
import { Bola } from '../components/Logo.jsx'

/** Tela 1 · Inicio */
export default function Inicio() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col px-6 py-10">
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <span className="mb-6 inline-flex size-24 items-center justify-center rounded-full bg-white ring-2 ring-tinta">
          <Bola className="size-14 text-tinta" />
        </span>
        <h1 className="text-4xl font-extrabold tracking-tight">Racha</h1>
        <p className="mt-3 text-gray-600">
          Sua pelada organizada.
          <br />
          Times justos com IA.
        </p>
      </div>
      <div className="flex flex-col gap-3">
        <Botao para="/login">Entrar</Botao>
        <Botao para="/cadastro" variante="secundario">
          Criar conta
        </Botao>
      </div>
    </main>
  )
}
