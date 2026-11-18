import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { gruposApi, mensagemDeErro } from '../api/client.js'
import Abas from '../components/Abas.jsx'
import Avatar from '../components/Avatar.jsx'
import Aviso from '../components/Aviso.jsx'
import Carregando from '../components/Carregando.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import ListaPartidas from '../components/ListaPartidas.jsx'
import { POSICOES } from '../components/posicoes.js'

const NOME_POSICAO = Object.fromEntries(POSICOES.map((p) => [p.valor, p.nome]))

function CodigoConvite({ codigo }) {
  const [copiado, setCopiado] = useState(false)
  async function copiar() {
    try {
      await navigator.clipboard.writeText(codigo)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 1800)
    } catch {
      /* navegador sem permissao de clipboard: o codigo continua visivel */
    }
  }
  return (
    <button
      type="button"
      onClick={copiar}
      className="mt-2 inline-flex w-fit items-center gap-2 rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600 hover:bg-gray-200"
      title="Copiar código"
    >
      convite: <span className="font-mono font-bold text-tinta">{codigo}</span>
      <span aria-live="polite" className="text-campo-700">{copiado ? 'copiado!' : 'copiar'}</span>
    </button>
  )
}

function ListaMembros({ grupoId }) {
  const [membros, setMembros] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    gruposApi
      .membros(grupoId)
      .then(setMembros)
      .catch((e) => setErro(mensagemDeErro(e)))
  }, [grupoId])

  if (erro) return <Aviso>{erro}</Aviso>
  if (!membros) return <Carregando />

  return (
    <>
      <p className="mb-3 text-xs font-semibold tracking-wide text-gray-500 uppercase">Membros ({membros.length})</p>
      <ul className="divide-y divide-gray-100 rounded-2xl bg-white ring-1 ring-gray-200">
        {membros.map((m) => (
          <li key={m.id} className="flex items-center gap-3 px-4 py-3">
            <Avatar nome={m.nome} tamanho="size-9" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold">{m.nome}</p>
              <p className="text-xs text-gray-500">{NOME_POSICAO[m.posicao] ?? m.posicao}</p>
            </div>
            {m.papel === 'organizador' && (
              <span className="rounded-full bg-campo-50 px-2 py-0.5 text-[11px] font-bold text-campo-700 ring-1 ring-campo-100">
                organizador
              </span>
            )}
          </li>
        ))}
      </ul>
    </>
  )
}

function EmBreve({ titulo, texto }) {
  return (
    <div className="rounded-2xl border-2 border-dashed border-gray-300 px-6 py-10 text-center">
      <p className="font-semibold">{titulo}</p>
      <p className="mt-1 text-sm text-gray-500">{texto}</p>
    </div>
  )
}

/** Tela 6 · Pagina do grupo (abas Partidas / Membros / Ranking) */
export default function PaginaGrupo() {
  const { id } = useParams()
  // key: trocar de grupo remonta a pagina e zera o estado
  return <Grupo key={id} id={id} />
}

function Grupo({ id }) {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') ?? 'partidas'
  const [grupo, setGrupo] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    gruposApi
      .detalhe(id)
      .then(setGrupo)
      .catch((e) =>
        setErro(e.response?.status === 404 ? 'Grupo não encontrado ou você não faz parte dele.' : mensagemDeErro(e)),
      )
  }, [id])

  if (erro)
    return (
      <>
        <Cabecalho titulo="Ops" voltar="/grupos" />
        <Aviso>{erro}</Aviso>
      </>
    )
  if (!grupo) return <Carregando />

  return (
    <>
      <Cabecalho
        titulo={grupo.nome}
        subtitulo={`${grupo.total_membros} ${grupo.total_membros === 1 ? 'jogador' : 'jogadores'}`}
        voltar="/grupos"
      >
        <CodigoConvite codigo={grupo.codigo_convite} />
      </Cabecalho>

      <Abas
        rotulo="Seções do grupo"
        ativa={aba}
        onChange={(valor) => setParams(valor === 'partidas' ? {} : { aba: valor }, { replace: true })}
        abas={[
          { valor: 'partidas', rotulo: 'Partidas' },
          { valor: 'membros', rotulo: 'Membros' },
          { valor: 'ranking', rotulo: 'Ranking' },
        ]}
      />

      <section className="mt-6" role="tabpanel">
        {aba === 'partidas' && <ListaPartidas grupo={grupo} />}
        {aba === 'membros' && <ListaMembros grupoId={grupo.id} />}
        {aba === 'ranking' && (
          <EmBreve titulo="Ranking ainda vazio" texto="Artilharia, vitórias e craques aparecem depois das primeiras partidas." />
        )}
      </section>
    </>
  )
}
