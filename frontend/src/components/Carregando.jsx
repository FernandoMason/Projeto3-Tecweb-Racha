export default function Carregando({ tela = false, texto = 'Carregando...' }) {
  return (
    <div role="status" className={`flex items-center justify-center gap-3 text-sm text-gray-500 ${tela ? 'min-h-dvh' : 'py-10'}`}>
      <span className="size-5 animate-spin rounded-full border-2 border-campo-700 border-r-transparent" aria-hidden />
      {texto}
    </div>
  )
}
