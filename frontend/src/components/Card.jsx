import { Link } from 'react-router-dom'

/** Cartao cinza claro. Com `para` vira um link clicavel. */
export default function Card({ para, destaque = false, className = '', children }) {
  const classes = [
    'block rounded-2xl p-4 transition',
    destaque ? 'bg-campo-50 ring-1 ring-campo-700' : 'bg-white ring-1 ring-gray-200',
    para ? 'hover:ring-gray-400 focus-visible:outline-2 focus-visible:outline-campo-700' : '',
    className,
  ].join(' ')

  if (para) {
    return (
      <Link to={para} className={classes}>
        {children}
      </Link>
    )
  }
  return <div className={classes}>{children}</div>
}
