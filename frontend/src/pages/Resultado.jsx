import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { mensagemDeErro, partidasApi } from '../api/client.js'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Carregando from '../components/Carregando.jsx'
import Contador from '../components/Contador.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import Placar from '../components/Placar.jsx'
import { dataHora } from '../components/partida.js'

const CONTRA = 'contra' // gol contra / sem autor

const chave = (timeId, membroId) => `${timeId}:${membroId ?? CONTRA}`

/** Gols ja lancados -> { "timeId:membroId": quantidade } */
function golsIniciais(resultado) {
  const gols = {}
  for (const g of resultado?.gols ?? []) gols[chave(g.time, g.jogador)] = g.quantidade
  return gols
}

/** Tela 11 · Resultado: o organizador marca os gols de cada jogador; o placar sai da soma. */
export default function PaginaResultado() {
  const { id } = useParams()
  return <Resultado key={id} id={id} />
}

function Resultado({ id }) {
  const navigate = useNavigate()
  const [partida, setPartida] = useState(null)
  const [gols, setGols] = useState({})
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    partidasApi
      .detalhe(id)
      .then((p) => {
        setPartida(p)
        setGols(golsIniciais(p.resultado))
      })
      .catch((e) => setErro(mensagemDeErro(e)))
  }, [id])

  if (!partida && erro)
    return (
      <>
        <Cabecalho titulo="Ops" voltar={`/partidas/${id}`} />
        <Aviso>{erro}</Aviso>
      </>
    )
  if (!partida) return <Carregando />

  if (!partida.eh_organizador || !['publicada', 'encerrada'].includes(partida.status)) {
    return (
      <>
        <Cabecalho titulo="Resultado" voltar={`/partidas/${id}`} />
        <Aviso>
          {partida.eh_organizador
            ? 'Publique os times antes de lançar o resultado.'
            : 'Só o organizador lança o resultado.'}
        </Aviso>
      </>
    )
  }

  const placar = partida.times.map((t) => ({
    time_id: t.id,
    nome: t.nome,
    cor: t.cor,
    gols: Object.entries(gols)
      .filter(([k]) => k.startsWith(`${t.id}:`))
      .reduce((s, [, n]) => s + n, 0),
  }))
  const ordenado = [...placar].sort((a, b) => b.gols - a.gols)
  const vencedor = ordenado.length > 1 && ordenado[0].gols > ordenado[1].gols ? ordenado[0] : null

  const mudar = (timeId, membroId) => (n) => setGols((g) => ({ ...g, [chave(timeId, membroId)]: n }))

  async function salvar() {
    setErro('')
    setSalvando(true)
    const lista = Object.entries(gols)
      .filter(([, n]) => n > 0)
      .map(([k, n]) => {
        const [time, jogador] = k.split(':')
        return { time: Number(time), jogador: jogador === CONTRA ? null : Number(jogador), quantidade: n }
      })
    try {
      await partidasApi.lancarResultado(id, lista)
      navigate(`/partidas/${id}/cronica`, { replace: true }) // a tela pos-jogo pede a cronica a IA
    } catch (e) {
      setErro(mensagemDeErro(e))
      setSalvando(false)
    }
  }

  return (
    <>
      <Cabecalho titulo="Resultado" subtitulo={`${partida.grupo_nome} · ${dataHora(partida.data_hora)}`} voltar={`/partidas/${id}`} />

      <div className="flex flex-col gap-6">
        <section className="flex flex-col gap-2">
          <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">Placar final</p>
          <Placar placar={placar} vencedor={vencedor} />
          <p className="text-xs text-gray-500">O placar é a soma dos gols marcados abaixo.</p>
        </section>

        {partida.times.map((t) => (
          <section key={t.id} className="overflow-hidden rounded-2xl bg-white ring-1 ring-gray-200">
            <header className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
              <span className="size-3 rounded-full ring-1 ring-gray-300" style={{ backgroundColor: t.cor }} />
              <h2 className="font-extrabold">Gols do {t.nome}</h2>
            </header>
            <ul className="divide-y divide-gray-100">
              {t.jogadores.map((j) => (
                <LinhaGol
                  key={j.membro_id}
                  nome={j.nome}
                  detalhe={j.posicao}
                  valor={gols[chave(t.id, j.membro_id)] ?? 0}
                  onChange={mudar(t.id, j.membro_id)}
                />
              ))}
              <LinhaGol
                nome="Gol contra / sem autor"
                detalhe={`soma no placar do ${t.nome}`}
                valor={gols[chave(t.id, null)] ?? 0}
                onChange={mudar(t.id, null)}
                apagado
              />
            </ul>
          </section>
        ))}

        <Aviso>{erro}</Aviso>
        <Botao onClick={salvar} carregando={salvando}>
          Salvar e gerar crônica
        </Botao>
      </div>
    </>
  )
}

function LinhaGol({ nome, detalhe, valor, onChange, apagado = false }) {
  return (
    <li className="flex items-center gap-3 px-4 py-2">
      <div className="min-w-0 flex-1">
        <p className={`truncate text-sm font-semibold ${apagado ? 'text-gray-500' : ''}`}>{nome}</p>
        <p className="text-[11px] text-gray-400">{detalhe}</p>
      </div>
      <Contador compacto rotulo={`gols de ${nome}`} valor={valor} onChange={onChange} min={0} max={30} />
    </li>
  )
}
