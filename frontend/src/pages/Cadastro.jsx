import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errosDosCampos, mensagemDeErro } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Campo from '../components/Campo.jsx'
import SeletorPosicao from '../components/SeletorPosicao.jsx'

/** Tela 3 · Cadastro */
export default function Cadastro() {
  const { cadastrar } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ nome: '', email: '', senha: '', posicao: 'MEI' })
  const [erros, setErros] = useState({})
  const [erroGeral, setErroGeral] = useState('')
  const [enviando, setEnviando] = useState(false)

  const mudar = (campo) => (e) => setForm((f) => ({ ...f, [campo]: e.target.value }))

  async function enviar(e) {
    e.preventDefault()
    setErros({})
    setErroGeral('')
    setEnviando(true)
    try {
      await cadastrar(form)
      navigate('/grupos', { replace: true })
    } catch (err) {
      const porCampo = errosDosCampos(err)
      setErros(porCampo)
      // erros de validacao da senha chegam em non_field_errors
      setErroGeral(porCampo.non_field_errors ?? (Object.keys(porCampo).length ? '' : mensagemDeErro(err)))
    } finally {
      setEnviando(false)
    }
  }

  const completo = form.nome.trim() && form.email && form.senha

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-6 py-10">
      <Link to="/" className="mb-8 w-fit text-xs font-semibold text-gray-500 hover:text-tinta">
        ← Voltar
      </Link>
      <h1 className="text-2xl font-extrabold tracking-tight">Criar conta</h1>
      <p className="mt-1 text-sm text-gray-500">Leva menos de um minuto.</p>

      <form onSubmit={enviar} className="mt-8 flex flex-col gap-4" noValidate>
        <Campo rotulo="Nome" autoComplete="name" value={form.nome} onChange={mudar('nome')} erro={erros.nome} />
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={mudar('email')}
          erro={erros.email}
        />
        <Campo
          rotulo="Senha"
          type="password"
          autoComplete="new-password"
          value={form.senha}
          onChange={mudar('senha')}
          erro={erros.senha}
          dica="Pelo menos 8 caracteres, não só números."
        />
        <SeletorPosicao valor={form.posicao} onChange={(posicao) => setForm((f) => ({ ...f, posicao }))} />
        <Aviso>{erroGeral}</Aviso>
        <Botao type="submit" carregando={enviando} disabled={!completo} className="mt-2">
          Criar conta
        </Botao>
      </form>

      <p className="mt-8 text-center text-sm text-gray-500">
        Já tem conta?{' '}
        <Link to="/login" className="font-bold text-tinta hover:underline">
          Entrar
        </Link>
      </p>
    </main>
  )
}
