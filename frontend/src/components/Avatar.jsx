const CORES = ['bg-campo-100 text-campo-800', 'bg-amber-100 text-amber-800', 'bg-sky-100 text-sky-800', 'bg-rose-100 text-rose-800', 'bg-violet-100 text-violet-800']

function iniciais(nome = '') {
  const partes = nome.trim().split(/\s+/)
  return ((partes[0]?.[0] ?? '') + (partes.length > 1 ? partes.at(-1)[0] : '')).toUpperCase() || '?'
}

/** Bolinha com as iniciais; a cor e fixa por nome. */
export default function Avatar({ nome, tamanho = 'size-10' }) {
  const cor = CORES[[...(nome ?? '')].reduce((s, c) => s + c.charCodeAt(0), 0) % CORES.length]
  return (
    <span className={`${tamanho} ${cor} inline-flex shrink-0 items-center justify-center rounded-full text-sm font-bold`}>
      {iniciais(nome)}
    </span>
  )
}
