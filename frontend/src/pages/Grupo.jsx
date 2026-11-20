import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { gruposApi, mensagemDeErro } from '../api/client.js'
import Abas from '../components/Abas.jsx'
import Avatar from '../components/Avatar.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Carregando from '../components/Carregando.jsx'
import Contador from '../components/Contador.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import ListaPartidas from '../components/ListaPartidas.jsx'
import RankingGrupo from '../components/RankingGrupo.jsx'
import SeletorPosicao from '../components/SeletorPosicao.jsx'
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

function EditarMembro({ grupoId, membro, onSalvo, onCancelar }) {
  const [posicao, setPosicao] = useState(membro.posicao)
  const [nota, setNota] = useState(membro.nota)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const mudou = posicao !== membro.posicao || nota !== membro.nota

  async function salvar(e) {
    e.preventDefault()
    setSalvando(true)
    setErro('')
    try {
      onSalvo(await gruposApi.editarMembro(grupoId, membro.id, { posicao, nota }))
    } catch (err) {
      setErro(mensagemDeErro(err))
      setSalvando(false)
    }
  }

  return (
    <form onSubmit={salvar} className="flex flex-col gap-4 bg-gray-50 px-4 py-4" aria-label={`Editar ${membro.nome}`}>
      <SeletorPosicao valor={posicao} onChange={setPosicao} rotulo="Posição no grupo" />
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-gray-500">Nota (1 a 10)</p>
          <p className="text-[11px] text-gray-400">Só você vê. A IA usa para equilibrar os times.</p>
        </div>
        <Contador valor={nota} onChange={setNota} min={1} max={10} rotulo="nota" compacto />
      </div>
      <Aviso>{erro}</Aviso>
      <div className="grid grid-cols-2 gap-2">
        <Botao type="button" variante="secundario" onClick={onCancelar} disabled={salvando}>
          Cancelar
        </Botao>
        <Botao type="submit" carregando={salvando} disabled={!mudou}>
          Salvar
        </Botao>
      </div>
    </form>
  )
}

function ListaMembros({ grupoId, souOrganizador }) {
  const [membros, setMembros] = useState(null)
  const [erro, setErro] = useState('')
  const [editando, setEditando] = useState(null)
  const [salvo, setSalvo] = useState('')

  useEffect(() => {
    gruposApi
      .membros(grupoId)
      .then(setMembros)
      .catch((e) => setErro(mensagemDeErro(e)))
  }, [grupoId])

  function aoSalvar(atualizado) {
    setMembros((lista) => lista.map((m) => (m.id === atualizado.id ? atualizado : m)))
    setEditando(null)
    setSalvo(`${atualizado.nome} atualizado.`)
  }

  if (erro) return <Aviso>{erro}</Aviso>
  if (!membros) return <Carregando />

  return (
    <>
      <p className="mb-3 text-xs font-semibold tracking-wide text-gray-500 uppercase">Membros ({membros.length})</p>
      {souOrganizador && (
        <p className="mb-3 text-xs text-gray-500">
          Toque em um jogador para ajustar a posição e a nota. As notas só aparecem para você.
        </p>
      )}
      {salvo && (
        <div className="mb-3">
          <Aviso tipo="ok">{salvo}</Aviso>
        </div>
      )}
      <ul className="divide-y divide-gray-100 overflow-hidden rounded-2xl bg-white ring-1 ring-gray-200">
        {membros.map((m) => {
          const aberto = editando === m.id
          const conteudo = (
            <>
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
              {m.nota != null && (
                <span
                  className="rounded bg-gray-100 px-1.5 py-0.5 text-xs font-bold text-gray-700 tabular-nums"
                  title="Nota"
                >
                  {m.nota}
                </span>
              )}
            </>
          )
          return (
            <li key={m.id}>
              {souOrganizador ? (
                <button
                  type="button"
                  onClick={() => {
                    setSalvo('')
                    setEditando(aberto ? null : m.id)
                  }}
                  aria-expanded={aberto}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-campo-700"
                >
                  {conteudo}
                  <span className="text-xs font-semibold text-campo-700">{aberto ? 'fechar' : 'editar'}</span>
                </button>
              ) : (
                <div className="flex items-center gap-3 px-4 py-3">{conteudo}</div>
              )}
              {aberto && (
                <EditarMembro
                  key={m.id}
                  grupoId={grupoId}
                  membro={m}
                  onSalvo={aoSalvar}
                  onCancelar={() => setEditando(null)}
                />
              )}
            </li>
          )
        })}
      </ul>
    </>
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
        {aba === 'membros' && <ListaMembros grupoId={grupo.id} souOrganizador={grupo.meu_papel === 'organizador'} />}
        {aba === 'ranking' && <RankingGrupo grupoId={grupo.id} />}
      </section>
    </>
  )
}
