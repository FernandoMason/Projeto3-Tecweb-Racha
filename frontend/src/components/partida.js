// Formatacao usada nas telas de partida, sorteio e resultado.

const DIAS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
const dois = (n) => String(n).padStart(2, '0')

/** "Qui 20/11" */
export function dataCurta(iso) {
  const d = new Date(iso)
  return `${DIAS[d.getDay()]} ${dois(d.getDate())}/${dois(d.getMonth() + 1)}`
}

/** "20h" ou "20h30" */
export function hora(iso) {
  const d = new Date(iso)
  return d.getMinutes() ? `${d.getHours()}h${dois(d.getMinutes())}` : `${d.getHours()}h`
}

/** "Qui 20/11 · 20h" */
export function dataHora(iso) {
  return `${dataCurta(iso)} · ${hora(iso)}`
}

/** 7.4 -> "7,4" */
export function forca(valor) {
  return Number(valor ?? 0).toFixed(1).replace('.', ',')
}

/** "em 1h32", "em 3 dias", "agora" */
export function tempoAte(iso, agora = Date.now()) {
  const minutos = Math.round((new Date(iso).getTime() - agora) / 60000)
  if (minutos <= 0) return 'agora'
  if (minutos < 60) return `em ${minutos} min`
  if (minutos < 48 * 60) {
    const h = Math.floor(minutos / 60)
    const m = minutos % 60
    return m ? `em ${h}h${dois(m)}` : `em ${h}h`
  }
  return `em ${Math.round(minutos / 1440)} dias`
}

/** O horario ja passou? */
export function jaPassou(iso) {
  return new Date(iso).getTime() <= Date.now()
}

/** Etapa atual da partida (para a barra presenca > times > jogo > resultado). */
export function etapa(partida) {
  if (partida.status === 'encerrada') return 'resultado'
  if (partida.status === 'publicada') return jaPassou(partida.data_hora) ? 'jogo' : 'times'
  if (partida.status === 'rascunho' || partida.status === 'sorteando') return 'times'
  return 'presenca'
}

export const ROTULO_STATUS = {
  aberta: 'presença aberta',
  sorteando: 'IA montando os times',
  rascunho: 'times em conferência',
  publicada: 'times publicados',
  encerrada: 'encerrada',
}

/** Placar curto: "Verde 5 x 3 Preto" (ou "Verde 2 · Preto 1 · Azul 0" com mais times). */
export function placarCurto(placar) {
  if (!placar?.length) return ''
  if (placar.length === 2) return `${placar[0].nome} ${placar[0].gols} x ${placar[1].gols} ${placar[1].nome}`
  return placar.map((p) => `${p.nome} ${p.gols}`).join(' · ')
}
