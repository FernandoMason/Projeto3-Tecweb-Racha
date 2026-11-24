import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { mensagemDeErro, resultadosApi } from '../api/client.js'
import Avatar from './Avatar.jsx'
import Aviso from './Aviso.jsx'
import Botao from './Botao.jsx'
import Carregando from './Carregando.jsx'
import SeloIA from './SeloIA.jsx'
import Vazio from './Vazio.jsx'
import { falar, parar, pararSeFor, temVoz, useNarrando } from './narrador.js'

/** Mural da partida (#44): narrações publicadas, a mais nova primeiro. Fica na tela pós-jogo. */
export default function MuralNarracoes({ partidaId }) {
  const [narracoes, setNarracoes] = useState(null)
  const [erro, setErro] = useState('')
  const secao = useRef(null)
  const { hash } = useLocation()

  const buscar = useCallback(
    () =>
      resultadosApi
        .narracoes(partidaId)
        .then(setNarracoes)
        .catch((e) => setErro(mensagemDeErro(e))),
    [partidaId],
  )

  useEffect(() => {
    buscar()
  }, [buscar])

  // voltou da tela 13 depois de publicar (/cronica#mural): rola até o mural
  const carregou = narracoes !== null
  useEffect(() => {
    if (carregou && hash === '#mural') secao.current?.scrollIntoView({ block: 'start' })
  }, [carregou, hash])

  function tentarDeNovo() {
    setErro('')
    setNarracoes(null)
    buscar()
  }

  const apagada = (id) => setNarracoes((lista) => lista.filter((n) => n.id !== id))

  return (
    <section ref={secao} id="mural" aria-labelledby="titulo-mural" className="flex scroll-mt-4 flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="titulo-mural" className="text-lg font-extrabold tracking-tight">
          Mural de narrações
        </h2>
        {narracoes?.length > 0 && <span className="text-xs font-semibold text-gray-500">{narracoes.length}</span>}
      </div>

      {erro ? (
        <div className="flex flex-col gap-3">
          <Aviso>{erro}</Aviso>
          <Botao variante="secundario" onClick={tentarDeNovo}>
            Tentar de novo
          </Botao>
        </div>
      ) : !narracoes ? (
        <Carregando texto="Carregando o mural..." />
      ) : narracoes.length === 0 ? (
        <Vazio titulo="Seja o primeiro a narrar um lance" compacto>
          Conte uma jogada da partida e a IA narra como no rádio. Dá para ouvir e publicar aqui.
        </Vazio>
      ) : (
        <>
          {!temVoz && <SemVoz />}
          <ul className="flex flex-col gap-3">
            {narracoes.map((n) => (
              <li key={n.id}>
                <ItemMural narracao={n} aoApagar={apagada} />
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function ItemMural({ narracao, aoApagar }) {
  const [confirmar, setConfirmar] = useState(false)
  const [apagando, setApagando] = useState(false)
  const [erro, setErro] = useState('')

  async function apagar() {
    setApagando(true)
    setErro('')
    try {
      await resultadosApi.apagarNarracao(narracao.id)
      aoApagar(narracao.id) // o BotaoOuvir sai da tela e para o áudio, se era este
    } catch (e) {
      setErro(mensagemDeErro(e))
      setApagando(false)
    }
  }

  const { autor, protagonista } = narracao
  return (
    <article className="flex flex-col gap-3 rounded-2xl bg-white p-4 ring-1 ring-gray-200">
      <div className="flex items-center gap-3">
        <Avatar nome={protagonista.nome} tamanho="size-9" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">Lance de {protagonista.nome}</p>
          <p className="truncate text-xs text-gray-500">
            {autor.membro === protagonista.membro ? 'contou o próprio lance' : `contado por ${autor.nome}`}
          </p>
        </div>
        <BotaoOuvir narracao={narracao} />
      </div>
      <TextoNarracao narracao={narracao} />

      {narracao.pode_apagar &&
        (confirmar ? (
          <div className="flex items-center justify-end gap-2 text-sm">
            <span className="mr-auto text-gray-600">Apagar esta narração?</span>
            <Botao variante="fantasma" largura={false} className="h-9 shrink-0 px-3" onClick={() => setConfirmar(false)}>
              Não
            </Botao>
            <button
              type="button"
              onClick={apagar}
              disabled={apagando}
              className="inline-flex h-9 shrink-0 items-center rounded-full bg-red-600 px-4 font-semibold whitespace-nowrap text-white hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700 disabled:opacity-50"
            >
              {apagando ? 'Apagando...' : 'Sim, apagar'}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmar(true)}
            className="w-fit self-end text-xs font-semibold text-gray-500 hover:text-red-700"
          >
            Apagar
          </button>
        ))}
      <Aviso>{erro}</Aviso>
    </article>
  )
}

/** Grito em destaque e o texto da narração. */
export function TextoNarracao({ narracao }) {
  return (
    <div className="flex flex-col gap-2">
      {narracao.grito && (
        <p className="text-xl leading-tight font-black tracking-tight text-balance text-campo-800">
          “{narracao.grito}”
        </p>
      )}
      <p className="leading-relaxed text-pretty text-gray-800">{narracao.narracao}</p>
      <SeloIA className="w-fit">narração da IA</SeloIA>
    </div>
  )
}

/** ▶ Ouvir / ■ Parar. Some quando o navegador não tem voz. Para o áudio ao sair da tela. */
export function BotaoOuvir({ narracao, grande = false }) {
  const tocando = useNarrando() === narracao.id

  // saiu da tela (ou a narração foi apagada): se era esta que tocava, para
  useEffect(() => () => pararSeFor(narracao.id), [narracao.id])

  if (!temVoz) return null
  const alternar = () => (tocando ? parar() : falar(narracao.id, narracao.grito, narracao.narracao))

  if (grande)
    return (
      <Botao variante="secundario" onClick={alternar} aria-pressed={tocando}>
        <span aria-hidden>{tocando ? '■' : '▶'}</span>
        {tocando ? 'Parar' : 'Ouvir a narração'}
      </Botao>
    )
  return (
    <button
      type="button"
      onClick={alternar}
      aria-pressed={tocando}
      aria-label={tocando ? `Parar a narração do lance de ${narracao.protagonista.nome}` : `Ouvir a narração do lance de ${narracao.protagonista.nome}`}
      className={`inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs font-bold ring-1 transition-colors focus-visible:outline-2 focus-visible:outline-campo-700 ${
        tocando ? 'bg-campo-700 text-white ring-campo-700' : 'bg-white text-tinta ring-gray-300 hover:bg-gray-50'
      }`}
    >
      <span aria-hidden>{tocando ? '■' : '▶'}</span>
      {tocando ? 'Parar' : 'Ouvir'}
    </button>
  )
}

export function SemVoz() {
  return (
    <p className="rounded-lg bg-gray-100 px-3 py-2 text-xs text-gray-600">
      Este navegador não tem voz para ler a narração em voz alta, mas o texto está aqui.
    </p>
  )
}
