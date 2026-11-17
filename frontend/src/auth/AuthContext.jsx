import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi, quandoDeslogar, tokens } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  // "carregando" enquanto confere se o token salvo ainda vale.
  const [carregando, setCarregando] = useState(() => Boolean(tokens.ler()?.access))

  const sair = useCallback(() => {
    tokens.limpar()
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
    () => ({ usuario, carregando, entrar, cadastrar, sair }),
    [usuario, carregando, entrar, cadastrar, sair],
  )

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return ctx
}
