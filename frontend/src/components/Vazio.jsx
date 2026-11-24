/** Estado vazio (caixa tracejada): mesmo visual em todas as telas. */
export default function Vazio({ titulo, children, compacto = false }) {
  return (
    <div className={`rounded-2xl border-2 border-dashed border-gray-300 px-6 text-center ${compacto ? 'py-8' : 'py-10'}`}>
      <p className="font-semibold text-balance">{titulo}</p>
      {children && <p className="mt-1 text-sm text-pretty text-gray-500">{children}</p>}
    </div>
  )
}
