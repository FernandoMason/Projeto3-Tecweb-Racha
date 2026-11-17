import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'
const CHAVE_TOKENS = 'racha.tokens'

export const tokens = {
  ler() {
    try {
      return JSON.parse(localStorage.getItem(CHAVE_TOKENS)) ?? null
    } catch {
      return null
    }
  },
  salvar(valor) {
    localStorage.setItem(CHAVE_TOKENS, JSON.stringify(valor))
  },
  limpar() {
    localStorage.removeItem(CHAVE_TOKENS)
  },
}

export const api = axios.create({ baseURL: BASE_URL })

// Coloca o access token em toda requisicao.
api.interceptors.request.use((config) => {
  const atual = tokens.ler()
  if (atual?.access) config.headers.Authorization = `Bearer ${atual.access}`
  return config
})

// Se o access expirou (401), tenta renovar uma vez com o refresh e repete a requisicao.
let renovando = null
let aoDeslogar = () => {}
export function quandoDeslogar(fn) {
  aoDeslogar = fn
}

api.interceptors.response.use(
  (resposta) => resposta,
  async (erro) => {
    const original = erro.config
    const atual = tokens.ler()
    const ehRotaDeAuth = original?.url?.startsWith('/auth/')
    if (erro.response?.status !== 401 || original._repetida || !atual?.refresh || ehRotaDeAuth) {
      return Promise.reject(erro)
    }
    original._repetida = true
    try {
      renovando ??= axios
        .post(`${BASE_URL}/auth/refresh/`, { refresh: atual.refresh })
        .finally(() => (renovando = null))
      const { data } = await renovando
      tokens.salvar({ ...atual, access: data.access })
      original.headers.Authorization = `Bearer ${data.access}`
      return api(original)
    } catch (e) {
      tokens.limpar()
      aoDeslogar()
      return Promise.reject(e)
    }
  },
)

/** Transforma o erro do DRF em uma mensagem curta para mostrar na tela. */
export function mensagemDeErro(erro, padrao = 'Algo deu errado. Tente de novo.') {
  const dados = erro?.response?.data
  if (!erro?.response) return 'Nao foi possivel falar com o servidor.'
  if (typeof dados === 'string') return padrao
  if (dados?.detail) {
    if (erro.response.status === 401 && dados.code !== 'token_not_valid') return 'E-mail ou senha incorretos.'
    return dados.detail
  }
  if (dados && typeof dados === 'object') {
    const primeiro = Object.values(dados).flat()[0]
    if (typeof primeiro === 'string') return primeiro
  }
  return padrao
}

/** Erros por campo ({email: '...', senha: '...'}) para destacar inputs. */
export function errosDosCampos(erro) {
  const dados = erro?.response?.data
  if (!dados || typeof dados !== 'object' || dados.detail) return {}
  return Object.fromEntries(
    Object.entries(dados).map(([campo, msgs]) => [campo, Array.isArray(msgs) ? msgs[0] : String(msgs)]),
  )
}

// --- Endpoints de contas e grupos ---
export const authApi = {
  cadastrar: (dados) => api.post('/auth/cadastro/', dados).then((r) => r.data),
  login: (email, password) => api.post('/auth/login/', { email, password }).then((r) => r.data),
  me: () => api.get('/auth/me/').then((r) => r.data),
}

export const gruposApi = {
  listar: () => api.get('/grupos/').then((r) => r.data),
  criar: (nome) => api.post('/grupos/', { nome }).then((r) => r.data),
  entrar: (codigo) => api.post('/grupos/entrar/', { codigo }).then((r) => r.data),
  detalhe: (id) => api.get(`/grupos/${id}/`).then((r) => r.data),
  membros: (id) => api.get(`/grupos/${id}/membros/`).then((r) => r.data),
}
