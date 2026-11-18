import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { errosDosCampos, mensagemDeErro, partidasApi } from '../api/client.js'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Campo from '../components/Campo.jsx'
import Contador from '../components/Contador.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import SeloIA from '../components/SeloIA.jsx'
import { dataHora, hora } from '../components/partida.js'

const ANTECEDENCIAS = [1, 2, 3, 6, 12, 24]

/** Proxima quinta (ou hoje, se for quinta) no formato do <input type="date">. */
function proximaQuinta() {
  const d = new Date()
  d.setDate(d.getDate() + ((4 - d.getDay() + 7) % 7))
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Tela 8 · Nova partida (so o organizador chega aqui) */
export default function NovaPartida() {
  const { id: grupoId } = useParams()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    data: proximaQuinta(),
    hora: '20:00',
    local: '',
    num_times: 2,
    jogadores_por_time: 5,
    antecedencia_horas: 2,
  })
  const [erros, setErros] = useState({})
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  const mudar = (campo) => (valor) => setForm((f) => ({ ...f, [campo]: valor }))

  // data + hora locais -> Date (o backend recebe em ISO/UTC)
  const quando = form.data && form.hora ? new Date(`${form.data}T${form.hora}`) : null
  const valido = quando && !Number.isNaN(quando.getTime())
  const sorteio = valido ? new Date(quando.getTime() - form.antecedencia_horas * 3600 * 1000) : null

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setErros({})
    setEnviando(true)
    try {
      const partida = await partidasApi.criar(grupoId, {
        data_hora: quando.toISOString(),
        local: form.local,
        num_times: form.num_times,
        jogadores_por_time: form.jogadores_por_time,
        antecedencia_horas: form.antecedencia_horas,
      })
      navigate(`/partidas/${partida.id}`, { replace: true })
    } catch (err) {
      setErros(errosDosCampos(err))
      setErro(mensagemDeErro(err))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <Cabecalho titulo="Nova partida" voltar={`/grupos/${grupoId}`} />

      <form onSubmit={enviar} className="flex flex-col gap-5" noValidate>
        <div className="grid grid-cols-2 gap-3">
          <Campo
            rotulo="Data"
            type="date"
            value={form.data}
            onChange={(e) => mudar('data')(e.target.value)}
            erro={erros.data_hora}
          />
          <Campo rotulo="Hora" type="time" value={form.hora} onChange={(e) => mudar('hora')(e.target.value)} />
        </div>

        <Campo
          rotulo="Local"
          placeholder="Arena Society"
          maxLength={120}
          value={form.local}
          onChange={(e) => mudar('local')(e.target.value)}
          erro={erros.local}
        />

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-gray-500">Times</span>
            <Contador rotulo="número de times" valor={form.num_times} onChange={mudar('num_times')} min={2} max={4} />
          </div>
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-gray-500">Jogadores por time</span>
            <Contador
              rotulo="jogadores por time"
              valor={form.jogadores_por_time}
              onChange={mudar('jogadores_por_time')}
              min={2}
              max={11}
            />
          </div>
        </div>

        <div className="rounded-2xl bg-violet-50 p-4 ring-1 ring-violet-200">
          <div className="flex items-center justify-between gap-3">
            <div>
              <SeloIA />
              <p className="mt-1 text-sm font-semibold">monta os times automaticamente</p>
            </div>
            <label className="sr-only" htmlFor="antecedencia">
              Quanto tempo antes do jogo
            </label>
            <select
              id="antecedencia"
              value={form.antecedencia_horas}
              onChange={(e) => mudar('antecedencia_horas')(Number(e.target.value))}
              className="h-10 rounded-full border border-violet-200 bg-white px-3 text-sm font-semibold"
            >
              {ANTECEDENCIAS.map((h) => (
                <option key={h} value={h}>
                  {h}h antes
                </option>
              ))}
            </select>
          </div>
          {sorteio && (
            <p className="mt-2 text-xs text-violet-900">
              Às {hora(sorteio.toISOString())} de {dataHora(sorteio.toISOString()).split(' · ')[0]} a IA divide quem
              confirmou em {form.num_times} times equilibrados e publica para o grupo. {form.num_times * form.jogadores_por_time}{' '}
              vagas; quem confirmar depois entra na lista de espera.
            </p>
          )}
        </div>

        <Aviso>{erro}</Aviso>
        <Botao type="submit" carregando={enviando} disabled={!valido || form.local.trim().length < 2}>
          Criar partida
        </Botao>
      </form>
    </>
  )
}
