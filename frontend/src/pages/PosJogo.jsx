import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { mensagemDeErro, partidasApi, resultadosApi } from '../api/client.js'
import Avatar from '../components/Avatar.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Carregando from '../components/Carregando.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import Placar from '../components/Placar.jsx'
import SeloIA from '../components/SeloIA.jsx'
import { dataHora, placarCurto } from '../components/partida.js'

/**
 * Tela 12 · Crônica da rodada: placar, crônica e craque escritos pela IA.
 *
 * Quando o organizador abre a tela e a crônica ainda não existe (acabou de lançar o placar)
 * ou está desatualizada (corrigiu o placar), ela é gerada na hora.
 */
export default function PaginaPosJogo() {
  const { id } = useParams()
  return <PosJogo key={id} id={id} />
}

function PosJogo({ id }) {
  const [partida, setPartida] = useState(null)
  const [cronica, setCronica] = useState(null)
  const [erro, setErro] = useState('') // nao deu para abrir a tela
  const [aviso, setAviso] = useState('') // a IA falhou ao gerar de novo, mas a tela continua
  const [gerando, setGerando] = useState(false)
  const gerandoAgora = useRef(false) // evita dois POSTs (StrictMode, clique duplo)

  const gerar = useCallback(async () => {
    if (gerandoAgora.current) return
    gerandoAgora.current = true
    setGerando(true)
    setAviso('')
    try {
      setCronica(await resultadosApi.gerarCronica(id))
    } catch (e) {
      // 503 = a IA falhou, mas a crônica boa que já existia foi mantida
      if (e.response?.status === 503 && e.response.data?.cronica) {
        setCronica(e.response.data.cronica)
        setAviso(`${e.response.data.detail} A crônica anterior foi mantida.`)
      } else {
        setAviso(mensagemDeErro(e))
      }
    } finally {
      gerandoAgora.current = false
      setGerando(false)
    }
  }, [id])

  useEffect(() => {
    let ativo = true
    async function carregar() {
      try {
        const p = await partidasApi.detalhe(id)
        let c = null
        if (p.resultado) {
          try {
            c = await resultadosApi.cronica(id)
          } catch (e) {
            if (e.response?.status !== 404) throw e // 404 = ainda não foi gerada
          }
        }
        if (!ativo) return
        setPartida(p)
        setCronica(c)
        if (p.resultado && p.eh_organizador && (!c || c.desatualizada)) gerar()
      } catch (e) {
        if (ativo) setErro(mensagemDeErro(e))
      }
    }
    carregar()
    return () => {
      ativo = false
    }
  }, [id, gerar])

  if (erro)
    return (
      <>
        <Cabecalho titulo="Ops" voltar={`/partidas/${id}`} />
        <Aviso>{erro}</Aviso>
      </>
    )
  if (!partida) return <Carregando />

  const { resultado } = partida
  const voltar = `/partidas/${id}`
  const subtitulo = `${partida.grupo_nome} · ${dataHora(partida.data_hora)}`

  if (!resultado)
    return (
      <>
        <Cabecalho titulo="Crônica da rodada" subtitulo={subtitulo} voltar={voltar} />
        <Neutro>A crônica sai depois que o organizador lançar o placar.</Neutro>
      </>
    )

  return (
    <>
      <Cabecalho titulo="Crônica da rodada" subtitulo={subtitulo} voltar={voltar} />

      <div className="flex flex-col gap-6">
        <section className="flex flex-col gap-3">
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

        {gerando ? (
          <section className="rounded-2xl bg-violet-50 ring-1 ring-violet-200">
            <Carregando texto="IA escrevendo a crônica…" />
            <p className="-mt-6 pb-6 text-center text-xs text-violet-900/70">Leva alguns segundos.</p>
          </section>
        ) : (
          <Texto cronica={cronica} organizador={partida.eh_organizador} />
        )}

        {!gerando && cronica?.craque && <Craque cronica={cronica} />}

        <Aviso>{aviso}</Aviso>

        <div className="flex flex-col gap-3">
          {!gerando && cronica?.status === 'ok' && (
            <Compartilhar cronica={cronica} placar={resultado.placar} grupo={partida.grupo_nome} />
          )}
          {partida.eh_organizador && !gerando && (
            <Botao variante={cronica?.status === 'ok' ? 'secundario' : 'campo'} onClick={gerar}>
              {cronica?.status === 'ok' ? 'Escrever outra crônica' : 'Tentar gerar de novo'}
            </Botao>
          )}
          <Botao variante="fantasma" para={voltar}>
            Voltar para a partida
          </Botao>
        </div>
      </div>
    </>
  )
}

function Neutro({ children }) {
  return <p className="rounded-2xl bg-gray-100 px-4 py-6 text-center text-sm text-gray-600">{children}</p>
}

function Texto({ cronica, organizador }) {
  if (!cronica)
    return <Neutro>A crônica ainda não foi escrita. Ela aparece aqui assim que o organizador gerar.</Neutro>

  if (cronica.status === 'erro')
    return (
      <section className="flex flex-col gap-1 rounded-2xl bg-amber-50 p-4 text-sm ring-1 ring-amber-200">
        <p className="font-bold text-amber-900">A IA não escreveu a crônica desta vez.</p>
        <p className="text-amber-900/80">
          {organizador ? cronica.erro : 'O organizador pode pedir de novo daqui a pouco.'}
        </p>
      </section>
    )

  return (
    <article className="flex flex-col gap-3 rounded-2xl bg-white p-5 ring-1 ring-gray-200">
      <SeloIA className="w-fit">crônica da IA</SeloIA>
      <h2 className="text-xl font-extrabold tracking-tight text-balance">{cronica.titulo}</h2>
      {cronica.texto.split('\n\n').map((paragrafo, i) => (
        <p key={i} className="leading-relaxed text-pretty text-gray-800">
          {paragrafo}
        </p>
      ))}
      {cronica.desatualizada && (
        <p className="text-xs text-gray-500">O placar foi corrigido depois desta crônica.</p>
      )}
    </article>
  )
}

function Craque({ cronica }) {
  const { craque } = cronica
  return (
    <section className="flex items-center gap-4 rounded-2xl bg-campo-50 p-4 ring-1 ring-campo-700">
      <Avatar nome={craque.nome} tamanho="size-14" />
      <div className="flex min-w-0 flex-col gap-1">
        <p className="text-xs font-semibold tracking-wide text-campo-800 uppercase">⭐ Craque da rodada</p>
        <p className="text-lg font-extrabold">{craque.nome}</p>
        {craque.motivo && <p className="text-sm text-gray-700">{craque.motivo}</p>}
        {cronica.origem_craque === 'ia' ? (
          <SeloIA className="w-fit">escolhido pela IA</SeloIA>
        ) : (
          <span className="w-fit rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-gray-600 ring-1 ring-gray-200">
            escolha automática
          </span>
        )}
      </div>
    </section>
  )
}

function Compartilhar({ cronica, placar, grupo }) {
  const [copiado, setCopiado] = useState(false)
  const texto = [
    `${cronica.titulo} (${grupo})`,
    placarCurto(placar),
    cronica.texto,
    cronica.craque ? `⭐ Craque da rodada: ${cronica.craque.nome}` : '',
  ]
    .filter(Boolean)
    .join('\n\n')

  async function compartilhar() {
    if (navigator.share) {
      try {
        await navigator.share({ title: cronica.titulo, text: texto })
        return
      } catch (e) {
        if (e.name === 'AbortError') return // a pessoa fechou o menu de compartilhar
      }
    }
    try {
      await navigator.clipboard.writeText(texto)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2500)
    } catch {
      // sem permissão de área de transferência: não há o que fazer
    }
  }

  return (
    <Botao onClick={compartilhar} aria-live="polite">
      {copiado ? 'Crônica copiada ✓' : 'Compartilhar'}
    </Botao>
  )
}
