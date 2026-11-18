/** Caixa de mensagem (erro por padrao). */
export default function Aviso({ tipo = 'erro', children }) {
  if (!children) return null
  const estilos = {
    erro: 'bg-red-50 text-red-700 ring-red-200',
    ok: 'bg-campo-50 text-campo-800 ring-campo-100',
  }
  return (
    <p role={tipo === 'erro' ? 'alert' : 'status'} className={`rounded-lg px-3 py-2 text-sm ring-1 ${estilos[tipo]}`}>
      {children}
    </p>
  )
}
