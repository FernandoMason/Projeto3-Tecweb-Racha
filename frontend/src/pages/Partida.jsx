import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { mensagemDeErro, partidasApi } from '../api/client.js'
import Avatar from '../components/Avatar.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Carregando from '../components/Carregando.jsx'
import CartaoTime from '../components/CartaoTime.jsx'
import Etapas from '../components/Etapas.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import Placar from '../components/Placar.jsx'
import SeloIA from '../components/SeloIA.jsx'
import { dataHora, etapa, hora, jaPassou, tempoAte } from '../components/partida.js'

/** Tela 9 · Partida e presenca (e, depois do sorteio, times e placar) */
export default function PaginaPartida() {
  const { id } = useParams()
  return <Partida key={id} id={id} />
}

function Partida({ id }) {
  const navigate = useNavigate()
  const [partida, setPartida] = useState(null)
  const [erro, setErro] = useState('')
  const [acao, setAcao] = useState('') // qual botao esta carregando
  const [, setRelogio] = useState(0)

  const carregar = useCallback(
    () =>
      partidasApi
        .detalhe(id)
        .then(setPartida)
        .catch((e) => setErro(e.response?.status === 404 ? 'Partida não encontrada.' : mensagemDeErro(e))),
    [id],
  )

  useEffect(() => {
    carregar()
  }, [carregar])

  // Enquanto a IA monta (montagem automatica disparada por outra pessoa), confere de novo a cada 3s.
  useEffect(() => {
    if (partida?.status !== 'sorteando') return
    const t = setTimeout(carregar, 3000)
    return () => clearTimeout(t)
  }, [partida, carregar])

  // Atualiza o "times saem em 1h32" a cada 30s.
  useEffect(() => {
    const t = setInterval(() => setRelogio((n) => n + 1), 30000)
    return () => clearInterval(t)
  }, [])

  async function executar(nome, fn) {
    setErro('')
    setAcao(nome)
    try {
      return await fn()
    } catch (e) {
      setErro(mensagemDeErro(e))
    } finally {
      setAcao('')
    }
  }

  const responder = (vou) => executar(vou ? 'vou' : 'nao', async () => setPartida(await partidasApi.presenca(id, vou)))

  const montarAgora = () =>
    executar('montar', async () => {
      await partidasApi.montarTimes(id)
      navigate(`/partidas/${id}/times`)
    })

  if (!partida && erro)
    return (
      <>
        <Cabecalho titulo="Ops" voltar="/grupos" />
        <Aviso>{erro}</Aviso>
      </>
    )
  if (!partida) return <Carregando />

  return (
    <>
      <Cabecalho
        titulo={dataHora(partida.data_hora)}
        subtitulo={`${partida.local} · ${partida.grupo_nome}`}
        voltar={`/grupos/${partida.grupo}`}
      />
      <Etapas atual={etapa(partida)} />

      <div className="mt-6 flex flex-col gap-6">
        <Aviso>{erro}</Aviso>

        {partida.status === 'aberta' && (
          <Presenca partida={partida} acao={acao} onResponder={responder} onMontar={montarAgora} />
        )}

        {partida.status === 'sorteando' && <Carregando texto="A IA está montando os times…" />}

        {partida.status === 'rascunho' &&
          (partida.eh_organizador ? (
            <div className="flex flex-col gap-3 rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-200">
              <SeloIA>times prontos</SeloIA>
              <p className="text-sm">A IA montou os times. Confira, troque alguém se precisar e confirme para o grupo ver.</p>
              <Botao para={`/partidas/${id}/times`}>Conferir times</Botao>
            </div>
          ) : (
            <AvisoNeutro>O organizador está conferindo os times. Eles aparecem aqui assim que forem confirmados.</AvisoNeutro>
          ))}

        {(partida.status === 'publicada' || partida.status === 'encerrada') && (
          <TimesEPlacar partida={partida} />
        )}
      </div>
    </>
  )
}

function AvisoNeutro({ children }) {
  return <p className="rounded-2xl bg-gray-100 px-4 py-6 text-center text-sm text-gray-600">{children}</p>
}

function Presenca({ partida, acao, onResponder, onMontar }) {
  const jaComecou = jaPassou(partida.data_hora)
  const faltam = partida.minimo_para_sortear - partida.total_confirmados
  const vagasLivres = partida.vagas - partida.confirmados.length

  return (
    <>
      <section aria-label="Sua presença" className="grid grid-cols-2 gap-3">
        <Botao
          variante={partida.minha_presenca === 'vou' ? 'campo' : 'secundario'}
          onClick={() => onResponder(true)}
          carregando={acao === 'vou'}
          disabled={jaComecou || Boolean(acao)}
          aria-pressed={partida.minha_presenca === 'vou'}
        >
          Vou {partida.minha_presenca === 'vou' && '✓'}
        </Botao>
        <Botao
          variante={partida.minha_presenca === 'nao_vou' ? 'primario' : 'secundario'}
          onClick={() => onResponder(false)}
          carregando={acao === 'nao'}
          disabled={jaComecou || Boolean(acao)}
          aria-pressed={partida.minha_presenca === 'nao_vou'}
        >
          Não vou
        </Botao>
      </section>

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
            Confirmados {partida.confirmados.length}/{partida.vagas}
          </p>
          <p className="text-xs font-semibold text-campo-700">
            {vagasLivres > 0 ? `+${vagasLivres} ${vagasLivres === 1 ? 'vaga' : 'vagas'}` : 'lotado'}
          </p>
        </div>
        <ListaJogadores jogadores={partida.confirmados} vazio="Ninguém confirmou ainda. Seja o primeiro!" />

        {partida.lista_espera.length > 0 && (
          <>
            <p className="mt-4 mb-2 text-xs font-semibold tracking-wide text-gray-500 uppercase">
              Lista de espera ({partida.lista_espera.length})
            </p>
            <ListaJogadores jogadores={partida.lista_espera} />
          </>
        )}
        {partida.nao_vao.length > 0 && (
          <p className="mt-3 text-xs text-gray-500">Não vão: {partida.nao_vao.map((j) => j.nome).join(', ')}</p>
        )}
      </section>

      <section className="flex flex-col gap-3 rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-200">
        <div className="flex items-center gap-2">
          <SeloIA />
          <p className="text-sm font-bold">Times saem {tempoAte(partida.sorteio_em)}</p>
        </div>
        <p className="text-sm text-violet-950">
          Às {hora(partida.sorteio_em)} a IA divide quem confirmou presença em {partida.num_times} times equilibrados,
          olhando posição e nota de cada um, e explica a escolha.
          {faltam > 0 && ` Faltam ${faltam} confirmações para dar jogo.`}
        </p>
        {partida.eh_organizador && (
          <>
            <Botao
              variante="campo"
              onClick={onMontar}
              carregando={acao === 'montar'}
              disabled={faltam > 0 || Boolean(acao)}
            >
              {acao === 'montar' ? 'A IA está montando…' : 'Montar times agora'}
            </Botao>
            <p className="text-center text-[11px] text-violet-900/70">Só você (organizador) vê este botão.</p>
          </>
        )}
      </section>
    </>
  )
}

function ListaJogadores({ jogadores, vazio }) {
  if (!jogadores.length) return <AvisoNeutro>{vazio}</AvisoNeutro>
  return (
    <ul className="flex flex-wrap gap-2">
      {jogadores.map((j) => (
        <li key={j.membro_id} className="flex items-center gap-2 rounded-full bg-white py-1 pr-3 pl-1 ring-1 ring-gray-200">
          <Avatar nome={j.nome} tamanho="size-7" />
          <span className="text-sm font-semibold">{j.nome}</span>
          <span className="text-[11px] text-gray-500">{j.posicao}</span>
        </li>
      ))}
    </ul>
  )
}

function TimesEPlacar({ partida }) {
  const { resultado } = partida
  return (
    <>
      {resultado && (
        <section className="flex flex-col gap-3">
          <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">Placar final</p>
          <Placar placar={resultado.placar} vencedor={resultado.vencedor} />
          {resultado.gols.length > 0 && (
            <ul className="flex flex-wrap gap-2 text-sm">
              {resultado.gols.map((g) => (
                <li key={g.id} className="rounded-full bg-white px-3 py-1 ring-1 ring-gray-200">
                  ⚽ {g.nome} {g.quantidade > 1 && <b>×{g.quantidade}</b>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">Times da rodada</p>
          <Link to={`/partidas/${partida.id}/times`} className="text-xs font-semibold text-violet-700 hover:underline">
            {partida.origem_times === 'ia' && '✦ '}Por que assim?
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {partida.times.map((t) => (
            <CartaoTime key={t.id} time={t} />
          ))}
        </div>
      </section>

      {partida.eh_organizador && (
        <Botao
          para={`/partidas/${partida.id}/resultado`}
          variante={resultado ? 'secundario' : 'primario'}
        >
          {resultado ? 'Corrigir resultado' : 'Lançar resultado'}
        </Botao>
      )}
    </>
  )
}
