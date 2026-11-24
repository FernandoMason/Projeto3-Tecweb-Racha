import { useEffect, useState } from 'react'
import { gruposApi, mensagemDeErro } from '../api/client.js'
import Avatar from '../components/Avatar.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Card from '../components/Card.jsx'
import Carregando from '../components/Carregando.jsx'
import { Cabecalho } from '../components/Layout.jsx'
import Vazio from '../components/Vazio.jsx'

/** Tela 4 · Meus grupos */
export default function MeusGrupos() {
  const [grupos, setGrupos] = useState(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    gruposApi
      .listar()
      .then(setGrupos)
      .catch((e) => setErro(mensagemDeErro(e)))
  }, [])

  return (
    <>
      <Cabecalho titulo="Meus grupos" />
      <Aviso>{erro}</Aviso>

      {grupos === null && !erro && <Carregando />}

      {grupos?.length === 0 && (
        <Vazio titulo="Você ainda não está em nenhum grupo">
          Crie a pelada da sua turma ou entre com o código de convite.
        </Vazio>
      )}

      {grupos?.length > 0 && (
        <ul className="flex flex-col gap-3">
          {grupos.map((g) => (
            <li key={g.id}>
              <Card para={`/grupos/${g.id}`} className="flex items-center gap-3">
                <Avatar nome={g.nome} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold">{g.nome}</p>
                  <p className="text-xs text-gray-500">
                    {g.total_membros} {g.total_membros === 1 ? 'jogador' : 'jogadores'}
                    {g.meu_papel === 'organizador' && ' · você organiza'}
                  </p>
                </div>
                <span aria-hidden className="text-gray-400">›</span>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-8 flex flex-col gap-3">
        <Botao para="/grupos/novo">+ Criar grupo</Botao>
        <Botao para="/grupos/novo?aba=entrar" variante="secundario">
          Entrar com código
        </Botao>
      </div>
    </>
  )
}
