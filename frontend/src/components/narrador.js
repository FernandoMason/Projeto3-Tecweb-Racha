import { useSyncExternalStore } from 'react'

/**
 * Voz da narração (#44): Web Speech API do navegador. O texto vem da IA no backend; o áudio sai aqui,
 * sem custo e sem arquivo. Só uma narração toca por vez: `useNarrando()` diz qual (o id) para os botões.
 */

export const temVoz = typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window

let tocando = null // id da narração que está tocando
let vez = 0 // muda a cada falar/parar: eventos atrasados de uma fala antiga são ignorados
const ouvintes = new Set()

function mudar(id) {
  tocando = id
  ouvintes.forEach((f) => f())
}

function assinar(f) {
  ouvintes.add(f)
  return () => ouvintes.delete(f)
}

/** Id da narração tocando agora (ou null). */
export function useNarrando() {
  return useSyncExternalStore(assinar, () => tocando)
}

function vozPtBr() {
  const vozes = window.speechSynthesis.getVoices()
  return (
    vozes.find((v) => v.lang === 'pt-BR') ||
    vozes.find((v) => v.lang?.replace('_', '-').toLowerCase() === 'pt-br') ||
    vozes.find((v) => v.lang?.toLowerCase().startsWith('pt')) ||
    null
  )
}

// Frases curtas: soa mais como narração e evita o corte de falas longas de algumas vozes do Chrome.
function frases(texto) {
  return (texto ?? '')
    .split(/(?<=[.!?…])\s+/)
    .map((f) => f.trim())
    .filter(Boolean)
}

/** Lê o grito (mais alto e animado) e depois a narração. Para o que estiver tocando antes. */
export function falar(id, grito, narracao) {
  if (!temVoz) return
  const sintese = window.speechSynthesis
  sintese.cancel()
  const minhaVez = ++vez
  const voz = vozPtBr()
  const partes = [
    ...(grito ? [{ texto: grito, tom: 1.35, velocidade: 1.05 }] : []),
    ...frases(narracao).map((texto) => ({ texto, tom: 1.15, velocidade: 1.12 })),
  ]
  if (!partes.length) return

  mudar(id)
  partes.forEach((p, i) => {
    const fala = new SpeechSynthesisUtterance(p.texto)
    fala.lang = 'pt-BR'
    if (voz) fala.voice = voz
    fala.pitch = p.tom
    fala.rate = p.velocidade
    if (i === partes.length - 1) {
      fala.onend = () => minhaVez === vez && mudar(null)
    }
    fala.onerror = () => minhaVez === vez && mudar(null)
    sintese.speak(fala)
  })
}

export function parar() {
  vez++
  if (temVoz) window.speechSynthesis.cancel()
  if (tocando !== null) mudar(null)
}

/** Para só se a narração `id` for a que está tocando (usado quando um botão sai da tela). */
export function pararSeFor(id) {
  if (tocando === id) parar()
}
