/** Numero com botoes - e + (jogadores por time, gols...). */
export default function Contador({ valor, onChange, min = 0, max = 99, rotulo, compacto = false }) {
  const tamanho = compacto ? 'size-8 text-base' : 'size-10 text-lg'
  const botao = `${tamanho} inline-flex items-center justify-center rounded-full font-bold transition disabled:opacity-30`
  return (
    <div className="inline-flex items-center gap-2" role="group" aria-label={rotulo}>
      <button
        type="button"
        className={`${botao} bg-gray-100 text-gray-700 hover:bg-gray-200`}
        onClick={() => onChange(Math.max(min, valor - 1))}
        disabled={valor <= min}
        aria-label={`Diminuir ${rotulo}`}
      >
        −
      </button>
      <span className={`${compacto ? 'w-6' : 'w-8'} text-center font-extrabold tabular-nums`} aria-live="polite">
        {valor}
      </span>
      <button
        type="button"
        className={`${botao} bg-tinta text-white hover:bg-gray-800`}
        onClick={() => onChange(Math.min(max, valor + 1))}
        disabled={valor >= max}
        aria-label={`Aumentar ${rotulo}`}
      >
        +
      </button>
    </div>
  )
}
