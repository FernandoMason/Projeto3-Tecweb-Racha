/** Controle segmentado (ex.: Partidas | Membros | Ranking). */
export default function Abas({ abas, ativa, onChange, rotulo }) {
  return (
    <div role="tablist" aria-label={rotulo} className="flex rounded-full bg-gray-100 p-1">
      {abas.map((aba) => {
        const selecionada = aba.valor === ativa
        return (
          <button
            key={aba.valor}
            role="tab"
            type="button"
            aria-selected={selecionada}
            onClick={() => onChange(aba.valor)}
            className={[
              'flex-1 rounded-full px-3 py-2 text-xs font-semibold transition',
              selecionada ? 'bg-white text-tinta shadow-sm ring-1 ring-gray-200' : 'text-gray-500 hover:text-tinta',
            ].join(' ')}
          >
            {aba.rotulo}
          </button>
        )
      })}
    </div>
  )
}
