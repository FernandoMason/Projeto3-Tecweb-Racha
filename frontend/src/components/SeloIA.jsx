/** Etiqueta "✦ IA" que marca tudo que foi feito pela IA. */
export default function SeloIA({ children = 'IA', className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-bold text-violet-800 ${className}`}
    >
      <span aria-hidden>✦</span>
      {children}
    </span>
  )
}
