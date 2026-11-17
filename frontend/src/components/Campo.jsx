import { useId } from 'react'

/** Input com rotulo e mensagem de erro. */
export default function Campo({ rotulo, erro, dica, className = '', ...props }) {
  const id = useId()
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={id} className="text-xs font-medium text-gray-500">
        {rotulo}
      </label>
      <input
        id={id}
        aria-invalid={Boolean(erro)}
        aria-describedby={erro || dica ? `${id}-msg` : undefined}
        className={[
          'h-11 rounded-lg border bg-white px-3 text-sm outline-none transition',
          'placeholder:text-gray-400 focus:border-campo-700 focus:ring-2 focus:ring-campo-100',
          erro ? 'border-red-500' : 'border-gray-300',
        ].join(' ')}
        {...props}
      />
      {(erro || dica) && (
        <p id={`${id}-msg`} className={`text-xs ${erro ? 'text-red-600' : 'text-gray-500'}`}>
          {erro || dica}
        </p>
      )}
    </div>
  )
}
