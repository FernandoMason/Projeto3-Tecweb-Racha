import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { gruposApi, mensagemDeErro } from '../api/client.js'
import Abas from '../components/Abas.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Campo from '../components/Campo.jsx'
import { Cabecalho } from '../components/Layout.jsx'

/** Tela 5 · Criar grupo ou entrar com codigo */
export default function CriarOuEntrar() {
  const [params, setParams] = useSearchParams()
  const aba = params.get('aba') === 'entrar' ? 'entrar' : 'criar'
  const navigate = useNavigate()

  const [nome, setNome] = useState('')
  const [codigo, setCodigo] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  function trocarAba(valor) {
    setErro('')
    setParams(valor === 'entrar' ? { aba: 'entrar' } : {}, { replace: true })
  }

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      const grupo = aba === 'criar' ? await gruposApi.criar(nome) : await gruposApi.entrar(codigo)
      navigate(`/grupos/${grupo.id}`, { replace: true })
    } catch (err) {
      setErro(mensagemDeErro(err))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <Cabecalho titulo={aba === 'criar' ? 'Novo grupo' : 'Entrar em um grupo'} voltar="/grupos" />
      <Abas
        rotulo="Criar ou entrar"
        ativa={aba}
        onChange={trocarAba}
        abas={[
          { valor: 'criar', rotulo: 'Criar' },
          { valor: 'entrar', rotulo: 'Tenho codigo' },
        ]}
      />

      <form onSubmit={enviar} className="mt-6 flex flex-col gap-4" noValidate>
        {aba === 'criar' ? (
          <Campo
            key="nome"
            rotulo="Nome do grupo"
            placeholder="Pelada de quinta"
            maxLength={80}
            autoFocus
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            dica="Voce vira o organizador e recebe um codigo para convidar a galera."
          />
        ) : (
          <Campo
            key="codigo"
            rotulo="Codigo de convite"
            placeholder="RACHA-7K2"
            autoCapitalize="characters"
            autoComplete="off"
            maxLength={12}
            autoFocus
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.toUpperCase())}
            dica="Peca o codigo para quem organiza a pelada."
          />
        )}
        <Aviso>{erro}</Aviso>
        <Botao
          type="submit"
          variante={aba === 'criar' ? 'primario' : 'secundario'}
          carregando={enviando}
          disabled={aba === 'criar' ? nome.trim().length < 3 : codigo.trim().length < 3}
        >
          {aba === 'criar' ? 'Criar grupo' : 'Entrar no grupo'}
        </Botao>
      </form>
    </>
  )
}
