import { useCallback, useEffect, useState } from 'react'
import { mensagemDeErro, resultadosApi } from '../api/client.js'
import Abas from './Abas.jsx'
import Avatar from './Avatar.jsx'
import Aviso from './Aviso.jsx'
import Botao from './Botao.jsx'
import Carregando from './Carregando.jsx'

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`

// Uma configuracao por sub-aba: de onde vem a lista, o numero grande e a linha de detalhe.
const LISTAS = {
  artilharia: {
    rotulo: 'Artilharia',
    numero: (i) => i.gols,
    unidade: (i) => (i.gols === 1 ? 'gol' : 'gols'),
    detalhe: (i) => `em ${plural(i.jogos, 'jogo', 'jogos')}`,
    vazio: 'Ninguém marcou gol ainda.',
  },
  vitorias: {
    rotulo: 'Vitórias',
    numero: (i) => i.vitorias,
    unidade: (i) => (i.vitorias === 1 ? 'vitória' : 'vitórias'),
    detalhe: (i) => `${i.vitorias}V · ${i.empates}E · ${i.derrotas}D em ${plural(i.jogos, 'jogo', 'jogos')}`,
    vazio: 'Nenhuma partida teve vencedor ainda.',
  },
  craques: {
    rotulo: 'Craques',
    numero: (i) => i.vezes,
    unidade: (i) => (i.vezes === 1 ? 'vez' : 'vezes'),
    detalhe: (i) => `em ${plural(i.jogos, 'jogo', 'jogos')}`,
    vazio: 'Nenhum craque escolhido ainda. O craque sai na crônica de cada rodada.',
  },
}

/** Tela 14 · Ranking do grupo: abas Artilharia, Vitórias e Craques (aba "Ranking" da página do grupo). */
export default function RankingGrupo({ grupoId }) {
  const [ranking, setRanking] = useState(null)
  const [erro, setErro] = useState('')
  const [lista, setLista] = useState('artilharia')

  const buscar = useCallback(
    () =>
      resultadosApi
        .ranking(grupoId)
        .then(setRanking)
        .catch((e) => setErro(mensagemDeErro(e))),
    [grupoId],
  )

  useEffect(() => {
    buscar()
  }, [buscar])

  function tentarDeNovo() {
    setErro('')
    setRanking(null)
    buscar()
  }

  if (erro)
    return (
      <div className="flex flex-col gap-3">
        <Aviso>{erro}</Aviso>
        <Botao variante="secundario" onClick={tentarDeNovo}>
          Tentar de novo
        </Botao>
      </div>
    )
  if (!ranking) return <Carregando texto="Carregando o ranking..." />

  if (ranking.jogos === 0)
    return (
      <div className="rounded-2xl border-2 border-dashed border-gray-300 px-6 py-10 text-center">
        <p className="font-semibold">Ranking ainda vazio</p>
        <p className="mt-1 text-sm text-gray-500">
          Artilharia, vitórias e craques aparecem depois que o organizador lançar o resultado da primeira partida.
        </p>
      </div>
    )

  const config = LISTAS[lista]
  const itens = ranking[lista]

  return (
    <div className="flex flex-col gap-4">
      <Abas
        rotulo="Rankings do grupo"
        ativa={lista}
        onChange={setLista}
        abas={Object.entries(LISTAS).map(([valor, c]) => ({ valor, rotulo: c.rotulo }))}
      />

      <p className="text-xs font-semibold tracking-wide text-gray-500 uppercase">
        {config.rotulo} · {plural(ranking.jogos, 'partida', 'partidas')} com resultado
      </p>

      {itens.length === 0 ? (
        <p className="rounded-2xl bg-gray-100 px-4 py-6 text-center text-sm text-gray-600">{config.vazio}</p>
      ) : (
        <ol className="divide-y divide-gray-100 rounded-2xl bg-white ring-1 ring-gray-200" aria-label={config.rotulo}>
          {itens.map((item) => {
            const empatado = itens.some((outro) => outro !== item && outro.colocacao === item.colocacao)
            return (
              <li key={item.membro} className="flex items-center gap-3 px-4 py-3">
                <Colocacao valor={item.colocacao} empatado={empatado} />
                <Avatar nome={item.nome} tamanho="size-9" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold">{item.nome}</p>
                  <p className="text-xs text-gray-500">{config.detalhe(item)}</p>
                </div>
                <p className="flex flex-col items-end leading-none">
                  <span className="text-2xl font-extrabold tabular-nums">{config.numero(item)}</span>
                  <span className="text-[11px] text-gray-500">{config.unidade(item)}</span>
                </p>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

function Colocacao({ valor, empatado }) {
  const cor =
    valor === 1
      ? 'bg-campo-700 text-white'
      : valor <= 3
        ? 'bg-campo-50 text-campo-800 ring-1 ring-campo-100'
        : 'bg-gray-100 text-gray-600'
  return (
    <span
      className={`inline-flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-extrabold tabular-nums ${cor}`}
      aria-label={`${valor}º lugar${empatado ? ', empatado' : ''}`}
      title={empatado ? 'empatado' : undefined}
    >
      {valor}º
    </span>
  )
}
