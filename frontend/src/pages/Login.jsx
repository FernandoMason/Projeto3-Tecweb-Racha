import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { mensagemDeErro } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'
import Aviso from '../components/Aviso.jsx'
import Botao from '../components/Botao.jsx'
import Campo from '../components/Campo.jsx'

/** Tela 2 · Login */
export default function Login() {
  const { entrar } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setErro('')
    setEnviando(true)
    try {
      await entrar(email, senha)
      navigate(location.state?.de ?? '/grupos', { replace: true })
    } catch (err) {
      setErro(mensagemDeErro(err))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center px-6 py-10">
      <Link to="/" className="mb-8 w-fit text-xs font-semibold text-gray-500 hover:text-tinta">
        ← Voltar
      </Link>
      <h1 className="text-2xl font-extrabold tracking-tight">Bem-vindo de volta</h1>
      <p className="mt-1 text-sm text-gray-500">Entre para ver suas peladas</p>

      <form onSubmit={enviar} className="mt-8 flex flex-col gap-4" noValidate>
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Campo
          rotulo="Senha"
          type="password"
          autoComplete="current-password"
          required
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
        />
        <Aviso>{erro}</Aviso>
        <Botao type="submit" carregando={enviando} disabled={!email || !senha} className="mt-2">
          Entrar
        </Botao>
      </form>

      <p className="mt-8 text-center text-sm text-gray-500">
        Nao tem conta?{' '}
        <Link to="/cadastro" className="font-bold text-tinta hover:underline">
          Criar conta
        </Link>
      </p>
    </main>
  )
}
