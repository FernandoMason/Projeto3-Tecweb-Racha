import { Link } from 'react-router-dom'

const VARIANTES = {
  primario: 'bg-tinta text-white hover:bg-gray-800 active:bg-gray-900',
  secundario: 'bg-white text-tinta ring-1 ring-inset ring-tinta hover:bg-gray-50',
  campo: 'bg-campo-700 text-white hover:bg-campo-800',
  fantasma: 'text-tinta hover:bg-gray-100',
}

/** Botao pilula do Racha. Com `para` vira um <Link>. */
export default function Botao({
  variante = 'primario',
  carregando = false,
  largura = true,
  para,
  className = '',
  children,
  ...props
}) {
  const classes = [
    'inline-flex items-center justify-center gap-2 rounded-full px-5 h-11 text-sm font-semibold',
    'transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-campo-700',
    'disabled:opacity-50 disabled:cursor-not-allowed',
    largura ? 'w-full' : '',
    VARIANTES[variante],
    className,
  ].join(' ')

  if (para) {
    return (
      <Link to={para} className={classes} {...props}>
        {children}
      </Link>
    )
  }

  return (
    <button className={classes} disabled={carregando || props.disabled} {...props}>
      {carregando && (
        <span className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden />
      )}
      {children}
    </button>
  )
}
