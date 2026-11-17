/** Placar grande: "Verde 5 x 3 Preto" (com 3+ times vira uma linha por time). */
export default function Placar({ placar, vencedor }) {
  if (!placar?.length) return null
  if (placar.length === 2) {
    const [a, b] = placar
    return (
      <div className="flex items-center justify-center gap-4 rounded-2xl bg-white px-4 py-5 ring-1 ring-gray-200">
        <LadoPlacar time={a} venceu={vencedor?.time_id === a.time_id} />
        <span className="text-lg font-bold text-gray-400">x</span>
        <LadoPlacar time={b} venceu={vencedor?.time_id === b.time_id} invertido />
      </div>
    )
  }
  return (
    <ul className="divide-y divide-gray-100 rounded-2xl bg-white ring-1 ring-gray-200">
      {[...placar]
        .sort((x, y) => y.gols - x.gols)
        .map((t) => (
          <li key={t.time_id} className="flex items-center gap-3 px-4 py-3">
            <span className="size-3 rounded-full ring-1 ring-gray-300" style={{ backgroundColor: t.cor }} />
            <span className="font-bold">{t.nome}</span>
            <span className="ml-auto text-2xl font-extrabold tabular-nums">{t.gols}</span>
          </li>
        ))}
    </ul>
  )
}

function LadoPlacar({ time, venceu, invertido = false }) {
  return (
    <div className={`flex flex-1 items-center gap-3 ${invertido ? 'flex-row-reverse text-right' : ''}`}>
      <div className="flex min-w-0 flex-col">
        <span className="flex items-center gap-1.5 text-sm font-bold">
          <span className="size-3 shrink-0 rounded-full ring-1 ring-gray-300" style={{ backgroundColor: time.cor }} />
          {time.nome}
        </span>
        {venceu && <span className="text-[11px] font-semibold text-campo-700">venceu</span>}
      </div>
      <span className={`ml-auto text-4xl font-extrabold tabular-nums ${invertido ? 'mr-auto ml-0' : ''}`}>{time.gols}</span>
    </div>
  )
}
