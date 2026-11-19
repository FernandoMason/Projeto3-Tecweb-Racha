import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { mensagemDeErro, partidasApi, resultadosApi } from '../api/client.js'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Carregando from '../components/Carregando.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import { BotaoOuvir, SemVoz, TextoNarracao } from '../components/MuralNarracoes.jsx'
import SeloIA from '../components/SeloIA.jsx'
import { temVoz } from '../components/narrador.js'
import { placarCurto } from '../components/partida.js'

const LIMITE = 500
const EXEMPLO = 'Peguei a bola no meio, vi o goleiro adiantado e mandei de cobertura...'

/**
 * Tela 13 · Narrar lance: o jogador conta uma jogada, a IA narra como no rádio,
 * dá para ouvir (Web Speech API) e publicar no mural da partida.
 */
export default function PaginaNarrarLance() {
  const { id } = useParams()
  return <NarrarLance key={id} id={id} />
}

function NarrarLance({ id }) {
  const navigate = useNavigate()
  const [partida, setPartida] = useState(null)
  const [erroTela, setErroTela] = useState('')
  const [lance, setLance] = useState('')
  const [protagonista, setProtagonista] = useState('') // '' = eu mesmo
  const [rascunho, setRascunho] = useState(null)
  const [gerando, setGerando] = useState(false)
  const [publicando, setPublicando] = useState(false)
  const [erro, setErro] = useState('')
  const previa = useRef(null)

  useEffect(() => {
    let ativo = true
    partidasApi
      .detalhe(id)
      .then((p) => ativo && setPartida(p))
      .catch((e) => ativo && setErroTela(mensagemDeErro(e)))
    return () => {
      ativo = false
    }
  }, [id])

  useEffect(() => {
    if (rascunho) previa.current?.focus()
  }, [rascunho])

  const voltar = `/partidas/${id}/cronica`
  if (erroTela)
    return (
      <>
        <Cabecalho titulo="Ops" voltar={voltar} />
        <Aviso>{erroTela}</Aviso>
      </>
    )
  if (!partida) return <Carregando />

  const subtitulo = [partida.grupo_nome, placarCurto(partida.resultado?.placar)].filter(Boolean).join(' · ')
  if (!partida.resultado)
    return (
      <>
        <Cabecalho titulo="Narrar um lance" subtitulo={partida.grupo_nome} voltar={`/partidas/${id}`} />
        <p className="rounded-2xl bg-gray-100 px-4 py-6 text-center text-sm text-gray-600">
          Dá para narrar os lances depois que o organizador lançar o placar.
        </p>
      </>
    )

  const curto = lance.trim().length < 5

  async function gerar(e) {
    e?.preventDefault()
    if (curto || gerando) return
    setGerando(true)
    setErro('')
    try {
      const n = await resultadosApi.narrar(id, { lance: lance.trim(), protagonista: protagonista ? Number(protagonista) : null })
      setRascunho(n)
    } catch (e) {
      setErro(mensagemDeErro(e)) // o relato continua na caixa para tentar de novo
    } finally {
      setGerando(false)
    }
  }

  async function publicar() {
    setPublicando(true)
    setErro('')
    try {
      await resultadosApi.publicarNarracao(rascunho.id)
      navigate(`${voltar}#mural`)
    } catch (e) {
      setErro(mensagemDeErro(e))
      setPublicando(false)
    }
  }

  return (
    <>
      <Cabecalho titulo="Narrar um lance" subtitulo={subtitulo} voltar={voltar}>
        <p className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          <SeloIA /> texto da IA, áudio no seu navegador
        </p>
      </Cabecalho>

      <form onSubmit={gerar} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="lance" className="text-sm font-semibold">
            Como foi o lance?
          </label>
          <textarea
            id="lance"
            value={lance}
            onChange={(e) => setLance(e.target.value.slice(0, LIMITE))}
            maxLength={LIMITE}
            rows={4}
            placeholder={EXEMPLO}
            aria-describedby="lance-dica"
            className="resize-none rounded-2xl bg-white px-4 py-3 text-base ring-1 ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-campo-700 focus:outline-none"
          />
          <p id="lance-dica" className="flex justify-between text-xs text-gray-500">
            <span>Conte do seu jeito. A IA só narra o que você descrever.</span>
            <span aria-hidden>
              {lance.length}/{LIMITE}
            </span>
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="protagonista" className="text-sm font-semibold">
            Quem fez o lance?
          </label>
          <select
            id="protagonista"
            value={protagonista}
            onChange={(e) => setProtagonista(e.target.value)}
            className="h-11 rounded-full bg-white px-4 text-sm ring-1 ring-gray-300 focus:ring-2 focus:ring-campo-700 focus:outline-none"
          >
            <option value="">Eu</option>
            {partida.times.map((t) => (
              <optgroup key={t.id} label={t.nome}>
                {t.jogadores.map((j) => (
                  <option key={j.membro_id} value={j.membro_id}>
                    {j.nome}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {!rascunho && (
          <Botao type="submit" variante="campo" carregando={gerando} disabled={curto}>
            {gerando ? 'IA narrando…' : '✦ Gerar narração'}
          </Botao>
        )}
      </form>

      <div className="mt-4 flex flex-col gap-4">
        <Aviso>{erro}</Aviso>

        {rascunho && (
          <section
            ref={previa}
            tabIndex={-1}
            aria-label="Prévia da narração"
            className="flex flex-col gap-4 rounded-2xl bg-violet-50 p-5 ring-1 ring-violet-200 focus:outline-none"
          >
            <p className="text-xs font-semibold tracking-wide text-violet-900/70 uppercase">
              Prévia · lance de {rascunho.protagonista.nome}
            </p>
            <TextoNarracao narracao={rascunho} />
            {temVoz ? <BotaoOuvir narracao={rascunho} grande /> : <SemVoz />}
            <Botao variante="campo" carregando={publicando} onClick={publicar}>
              Publicar no mural
            </Botao>
            <Botao variante="fantasma" onClick={gerar} carregando={gerando} disabled={curto || publicando}>
              {gerando ? 'IA narrando…' : 'Gerar de novo'}
            </Botao>
            <p className="-mt-2 text-center text-xs text-gray-500">
              Mudou o relato? Edite a caixa acima e gere de novo. Só vai para o mural se você publicar.
            </p>
          </section>
        )}
      </div>
    </>
  )
}
