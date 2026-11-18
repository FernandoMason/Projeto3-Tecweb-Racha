const ETAPAS = [
  { valor: 'presenca', rotulo: 'presença' },
  { valor: 'times', rotulo: 'times' },
  { valor: 'jogo', rotulo: 'jogo' },
  { valor: 'resultado', rotulo: 'resultado' },
]

/** Barra de progresso da partida: presenca > times > jogo > resultado. */
export default function Etapas({ atual }) {
  const indice = ETAPAS.findIndex((e) => e.valor === atual)
  return (
    <ol className="flex gap-1.5" aria-label="Etapas da partida">
      {ETAPAS.map((e, i) => (
        <li key={e.valor} className="flex flex-1 flex-col gap-1" aria-current={i === indice ? 'step' : undefined}>
          <span className={`h-1.5 rounded-full ${i <= indice ? 'bg-campo-700' : 'bg-gray-200'}`} />
          <span className={`text-[11px] font-semibold ${i === indice ? 'text-campo-800' : 'text-gray-400'}`}>
            {e.rotulo}
          </span>
        </li>
      ))}
    </ol>
  )
}
