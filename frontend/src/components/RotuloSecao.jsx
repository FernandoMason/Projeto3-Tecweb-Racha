/** Rotulo pequeno em caixa alta que abre uma secao (ex.: PRÓXIMAS, PLACAR FINAL). */
export default function RotuloSecao({ className = '', children }) {
  return <p className={`text-xs font-semibold tracking-wide text-gray-500 uppercase ${className}`}>{children}</p>
}
