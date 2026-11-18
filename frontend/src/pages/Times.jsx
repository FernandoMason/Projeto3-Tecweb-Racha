import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { mensagemDeErro, partidasApi } from '../api/client.js'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Carregando from '../components/Carregando.jsx'
import CartaoTime from '../components/CartaoTime.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import SeloIA from '../components/SeloIA.jsx'
import { dataHora, forca, hora } from '../components/partida.js'

const LIMITE_EQUILIBRIO = 0.5 // mesmo limite do backend (partidas/equilibrio.py)

/** Tela 10 · Times da rodada: times, forca, explicacao da IA; refazer, trocar e confirmar */
export default function PaginaTimes() {
  const { id } = useParams()
  return <Times key={id} id={id} />
}

function Times({ id }) {
  const [partida, setPartida] = useState(null)
  const [erro, setErro] = useState('')
  const [acao, setAcao] = useState('')
  const [trocando, setTrocando] = useState(false)
  const [escolhido, setEscolhido] = useState(null) // primeiro jogador clicado no modo trocar

  useEffect(() => {
    partidasApi
      .detalhe(id)
      .then(setPartida)
      .catch((e) => setErro(mensagemDeErro(e)))
  }, [id])

  async function executar(nome, fn) {
    setErro('')
    setAcao(nome)
    try {
      setPartida(await fn())
    } catch (e) {
      setErro(mensagemDeErro(e))
    } finally {
      setAcao('')
    }
  }

  const sortearDeNovo = () => {
    setTrocando(false)
    setEscolhido(null)
    executar('sortear', () => partidasApi.montarTimes(id))
  }
  const confirmar = () => executar('confirmar', () => partidasApi.confirmarTimes(id))

  function escolher(membroId) {
    if (escolhido === null) return setEscolhido(membroId)
    if (escolhido === membroId) return setEscolhido(null)
    const timeDe = (m) => partida.times.find((t) => t.jogadores.some((j) => j.membro_id === m))?.id
    if (timeDe(escolhido) === timeDe(membroId)) return setEscolhido(membroId) // mesmo time: troca a selecao
    const primeiro = escolhido
    setEscolhido(null)
    executar('trocar', () => partidasApi.trocar(id, primeiro, membroId))
  }

  if (!partida && erro)
    return (
      <>
        <Cabecalho titulo="Ops" voltar={`/partidas/${id}`} />
        <Aviso>{erro}</Aviso>
      </>
    )
  if (!partida) return <Carregando />

  const organizador = partida.eh_organizador
  const podeMexer = organizador && ['rascunho', 'publicada'].includes(partida.status)
  const semTimes = partida.times.length === 0
  const equilibrado = partida.diferenca_forca != null && partida.diferenca_forca <= LIMITE_EQUILIBRIO
  const daIA = partida.origem_times === 'ia'

  return (
    <>
      <Cabecalho
        titulo="Times da rodada"
        subtitulo={`${partida.grupo_nome} · ${dataHora(partida.data_hora)}`}
        voltar={`/partidas/${id}`}
      >
        {!semTimes && (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {daIA ? <SeloIA>montado pela IA</SeloIA> : <SeloIA className="bg-gray-200 text-gray-700">plano B (sem IA)</SeloIA>}
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600">
              {partida.status === 'rascunho'
                ? 'rascunho · só você vê'
                : `publicado ${partida.times_publicados_em ? hora(partida.times_publicados_em) : ''} · todos veem`}
            </span>
          </div>
        )}
      </Cabecalho>

      {acao === 'sortear' ? (
        <div className="rounded-2xl bg-violet-50 px-6 py-12 text-center ring-1 ring-violet-200">
          <Carregando texto="A IA está montando novos times…" />
          <p className="text-xs text-violet-900/70">Ela confere posições e notas e o Racha valida o equilíbrio.</p>
        </div>
      ) : semTimes ? (
        <p className="rounded-2xl bg-gray-100 px-4 py-6 text-center text-sm text-gray-600">
          {partida.status === 'rascunho'
            ? 'O organizador está conferindo os times.'
            : 'Os times ainda não foram montados.'}
        </p>
      ) : (
        <div className="flex flex-col gap-5">
          {trocando && (
            <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-200">
              {escolhido === null
                ? 'Toque em um jogador e depois em outro de outro time para trocá-los.'
                : 'Agora toque no jogador do outro time.'}
            </p>
          )}

          <div className={`grid gap-3 ${partida.times.length === 2 ? 'grid-cols-2' : 'sm:grid-cols-2'}`}>
            {partida.times.map((t) => (
              <CartaoTime
                key={t.id}
                time={t}
                selecionado={escolhido}
                onEscolher={trocando && acao !== 'trocar' ? escolher : undefined}
              />
            ))}
          </div>

          <section className="rounded-2xl bg-white p-4 ring-1 ring-gray-200">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold">Equilíbrio</span>
              <span className={`font-bold ${equilibrado ? 'text-campo-700' : 'text-amber-700'}`}>
                diferença {forca(partida.diferenca_forca)} · {equilibrado ? 'equilibrado' : 'desequilibrado'}
              </span>
            </div>
            <BarraEquilibrio times={partida.times} />
          </section>

          {partida.explicacao_ia && (
            <section
              className={`rounded-2xl p-4 ring-1 ${daIA ? 'bg-violet-50 ring-violet-200' : 'bg-gray-50 ring-gray-200'}`}
            >
              <p className="mb-1 flex items-center gap-2 text-sm font-bold">
                {daIA && <SeloIA />} Por que assim?
              </p>
              <p className="text-sm leading-relaxed text-gray-800">{partida.explicacao_ia}</p>
              {partida.ajustado_pelo_organizador && (
                <p className="mt-2 text-xs font-semibold text-amber-800">
                  O organizador trocou jogadores depois do sorteio; a força acima já considera a troca.
                </p>
              )}
            </section>
          )}
        </div>
      )}

      <div className="mt-6 flex flex-col gap-3">
        <Aviso>{erro}</Aviso>
        {podeMexer && !semTimes && (
          <>
            <div className="grid grid-cols-2 gap-3">
              <Botao variante="secundario" onClick={sortearDeNovo} carregando={acao === 'sortear'} disabled={Boolean(acao)}>
                ↻ Sortear de novo
              </Botao>
              <Botao
                variante={trocando ? 'campo' : 'secundario'}
                onClick={() => {
                  setTrocando((v) => !v)
                  setEscolhido(null)
                }}
                carregando={acao === 'trocar'}
                disabled={Boolean(acao) && acao !== 'trocar'}
                aria-pressed={trocando}
              >
                {trocando ? 'Pronto' : 'Trocar ⇄'}
              </Botao>
            </div>
            {partida.status === 'rascunho' && (
              <Botao onClick={confirmar} carregando={acao === 'confirmar'} disabled={Boolean(acao)}>
                Confirmar e publicar para o grupo
              </Botao>
            )}
            <p className="text-center text-[11px] text-gray-500">
              Sortear de novo e trocar: só o organizador. As notas aparecem só para você.
            </p>
          </>
        )}
      </div>
    </>
  )
}

/** Barra com a forca de cada time lado a lado. */
function BarraEquilibrio({ times }) {
  const total = times.reduce((s, t) => s + t.forca, 0) || 1
  return (
    <div className="mt-3 flex h-3 overflow-hidden rounded-full ring-1 ring-gray-200" aria-hidden>
      {times.map((t) => (
        <span key={t.id} style={{ width: `${(t.forca / total) * 100}%`, backgroundColor: t.cor }} />
      ))}
    </div>
  )
}
