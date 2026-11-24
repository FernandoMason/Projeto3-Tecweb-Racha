import { useEffect, useState } from 'react'
import { mensagemDeErro, partidasApi } from '../api/client.js'
import Aviso from './Aviso.jsx'
import Botao from './Botao.jsx'
import Card from './Card.jsx'
import Carregando from './Carregando.jsx'
import RotuloSecao from './RotuloSecao.jsx'
import Vazio from './Vazio.jsx'
import { ROTULO_STATUS, dataHora, hora, jaPassou, placarCurto } from './partida.js'

function ChipPresenca({ status }) {
  if (status === 'vou') return <span className="rounded-full bg-campo-100 px-2 py-0.5 text-[11px] font-bold text-campo-800">você vai</span>
  if (status === 'nao_vou') return <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-bold text-gray-500">você não vai</span>
  return <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-800">responda</span>
}

function ProximaPartida({ partida, destaque }) {
  const legenda =
    partida.status === 'aberta'
      ? `times saem às ${hora(partida.sorteio_em)}`
      : jaPassou(partida.data_hora) && partida.status === 'publicada'
        ? 'aguardando o resultado'
        : ROTULO_STATUS[partida.status]
  return (
    <Card para={`/partidas/${partida.id}`} destaque={destaque} className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2">
        <p className="font-bold">{dataHora(partida.data_hora)}</p>
        {partida.status === 'aberta' && <ChipPresenca status={partida.minha_presenca} />}
      </div>
      <p className="text-sm text-gray-600">
        {partida.local} · {partida.total_confirmados}/{partida.vagas} confirmados
      </p>
      <p className="text-xs font-semibold text-campo-700">{legenda}</p>
    </Card>
  )
}

/** Aba "Partidas" da tela do grupo: proximas em cima, encerradas embaixo. */
export default function ListaPartidas({ grupo }) {
  const [partidas, setPartidas] = useState(null)
  const [erro, setErro] = useState('')
  const organizador = grupo.meu_papel === 'organizador'

  useEffect(() => {
    partidasApi
      .doGrupo(grupo.id)
      .then(setPartidas)
      .catch((e) => setErro(mensagemDeErro(e)))
  }, [grupo.id])

  if (erro) return <Aviso>{erro}</Aviso>
  if (!partidas) return <Carregando />

  const proximas = partidas
    .filter((p) => p.status !== 'encerrada')
    .sort((a, b) => new Date(a.data_hora) - new Date(b.data_hora))
  const encerradas = partidas.filter((p) => p.status === 'encerrada')

  return (
    <div className="flex flex-col gap-6">
      {partidas.length === 0 && (
        <Vazio titulo="Nenhuma partida marcada">
          {organizador
            ? 'Marque o próximo jogo: a galera confirma presença e a IA monta os times.'
            : 'Quando o organizador marcar o próximo jogo, ele aparece aqui.'}
        </Vazio>
      )}

      {proximas.length > 0 && (
        <section>
          <RotuloSecao className="mb-3">Próximas</RotuloSecao>
          <ul className="flex flex-col gap-3">
            {proximas.map((p, i) => (
              <li key={p.id}>
                <ProximaPartida partida={p} destaque={i === 0} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {encerradas.length > 0 && (
        <section>
          <RotuloSecao className="mb-3">Encerradas</RotuloSecao>
          <ul className="flex flex-col gap-2">
            {encerradas.map((p) => (
              <li key={p.id}>
                <Card para={`/partidas/${p.id}`} className="flex items-center justify-between gap-3 py-3">
                  <span className="text-sm font-semibold">{dataHora(p.data_hora)}</span>
                  <span className="text-sm text-gray-600">{placarCurto(p.placar)}</span>
                </Card>
              </li>
            ))}
          </ul>
        </section>
      )}

      {organizador && <Botao para={`/grupos/${grupo.id}/partidas/nova`}>+ Nova partida</Botao>}
    </div>
  )
}
