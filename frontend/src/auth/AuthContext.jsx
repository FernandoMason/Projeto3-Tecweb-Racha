import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi, quandoDeslogar, tokens } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  // "carregando" enquanto confere se o token salvo ainda vale.
  const [carregando, setCarregando] = useState(() => Boolean(tokens.ler()?.access))
  // true depois de clicar em "Sair": a rota protegida manda para o inicio, nao para o login
  const [saiu, setSaiu] = useState(false)

  const sair = useCallback(() => {
    tokens.limpar()
    setSaiu(true)
    setUsuario(null)
  }, [])

  useEffect(() => {
    quandoDeslogar(() => setUsuario(null))
    if (!tokens.ler()?.access) return
    authApi
      .me()
      .then(setUsuario)
      .catch(() => tokens.limpar())
      .finally(() => setCarregando(false))
  }, [])

  const guardarSessao = useCallback(({ access, refresh, usuario: u }) => {
    tokens.salvar({ access, refresh })
    setSaiu(false)
    setUsuario(u)
    return u
  }, [])

  const entrar = useCallback(
    async (email, senha) => guardarSessao(await authApi.login(email, senha)),
    [guardarSessao],
  )

  const cadastrar = useCallback(
    async (dados) => guardarSessao(await authApi.cadastrar(dados)),
    [guardarSessao],
  )

  const valor = useMemo(
    () => ({ usuario, carregando, saiu, entrar, cadastrar, sair }),
    [usuario, carregando, saiu, entrar, cadastrar, sair],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return ctx
}
