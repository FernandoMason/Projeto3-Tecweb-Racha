import { POSICOES } from './posicoes.js'

/** Pilulas GOL / ZAG / MEI / ATA (radio group acessivel). */
export default function SeletorPosicao({ valor, onChange, rotulo = 'Posição preferida' }) {
  return (
    <fieldset className="flex flex-col gap-1.5">
      <legend className="mb-1.5 text-xs font-medium text-gray-500">{rotulo}</legend>
      <div className="grid grid-cols-4 gap-2">
        {POSICOES.map((p) => {
          const ativo = valor === p.valor
          return (
            <label
              key={p.valor}
              title={p.nome}
              className={[
                'flex h-10 cursor-pointer items-center justify-center rounded-full text-xs font-bold transition',
                'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-campo-700',
                ativo ? 'bg-tinta text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
              ].join(' ')}
            >
              <input
                type="radio"
                name="posicao"
                value={p.valor}
                checked={ativo}
                onChange={() => onChange(p.valor)}
                className="sr-only"
              />
              {p.valor}
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
