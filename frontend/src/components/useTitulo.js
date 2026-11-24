import { useEffect } from 'react'

const PADRAO = 'Racha · sua pelada organizada'

/** Titulo da aba do navegador: "Pelada de quinta · Racha". Volta ao padrao ao sair da tela. */
export default function useTitulo(titulo) {
  useEffect(() => {
    if (typeof titulo !== 'string' || !titulo) return
    document.title = `${titulo} · Racha`
    return () => {
      document.title = PADRAO
    }
  }, [titulo])
}
