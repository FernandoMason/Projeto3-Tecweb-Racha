/** Bola + "Racha". */
export function Bola({ className = 'size-6' }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <circle cx="32" cy="32" r="28" fill="#fff" stroke="currentColor" strokeWidth="4" />
      <path d="M32 18l12 9-4.5 15h-15L20 27z" fill="currentColor" />
    </svg>
  )
}

export default function Logo({ className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2 font-extrabold tracking-tight text-tinta ${className}`}>
      <Bola className="size-6 text-tinta" />
      Racha
    </span>
  )
}
