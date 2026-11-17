import { forca } from './partida.js'

/**
 * Um time do sorteio: cor, nome, forca (media das notas) e jogadores.
 * Com `onEscolher`, os jogadores viram botoes (modo "trocar").
 */
export default function CartaoTime({ time, selecionado, onEscolher, destacarForca = true }) {
  const claro = time.cor === '#e5e7eb'
  return (
    <section className="flex flex-col overflow-hidden rounded-2xl bg-white ring-1 ring-gray-200">
      <header
        className="flex items-center justify-between px-4 py-3"
        style={{ backgroundColor: time.cor, color: claro ? '#1f2937' : '#fff' }}
      >
        <h3 className="font-extrabold">{time.nome}</h3>
        {destacarForca && (
          <span className="text-xl font-extrabold tabular-nums" title="Força: média das notas">
            {forca(time.forca)}
          </span>
        )}
      </header>
      <ul className="flex flex-col divide-y divide-gray-100">
        {time.jogadores.map((j) => {
          const ativo = selecionado === j.membro_id
          const conteudo = (
            <>
              <span className="truncate font-semibold">{j.nome}</span>
              <span className="ml-auto flex items-center gap-2 text-xs text-gray-500">
                {j.posicao}
                {j.nota != null && (
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 font-bold text-gray-700 tabular-nums">{j.nota}</span>
                )}
              </span>
            </>
          )
          return (
            <li key={j.membro_id}>
              {onEscolher ? (
                <button
                  type="button"
                  onClick={() => onEscolher(j.membro_id)}
                  aria-pressed={ativo}
                  aria-label={`${j.nome}, ${j.posicao}, ${time.nome}`}
                  className={[
                    'flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm transition',
                    ativo ? 'bg-amber-100 ring-2 ring-amber-400 ring-inset' : 'hover:bg-gray-50',
                  ].join(' ')}
                >
                  {conteudo}
                </button>
              ) : (
                <div className="flex items-center gap-2 px-4 py-2.5 text-sm">{conteudo}</div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
