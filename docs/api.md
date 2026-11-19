# Contrato da API (#7)

Começou como proposta na Sprint 1 e agora descreve **o código que está na `main`** (atualizado em 19/11/2026).
Os exemplos de resposta são **respostas reais** da API: foram gerados chamando cada rota sobre os dados do
`python manage.py popular_racha`, com o Gemini de verdade (`gemini-3.5-flash-lite`) no sorteio, na crônica e na
narração, dentro de uma transação desfeita no fim. Listas longas foram cortadas com `…`.

O README tem as tabelas resumidas ("API (contas e grupos)" e "API (partidas, presença, sorteio e resultado)").
Aqui ficam os campos, as regras e os exemplos.

## Convenções

- Todas as rotas ficam em `/api/` e pedem `Authorization: Bearer <access>` (JWT), exceto cadastro, login e refresh.
  Sem token: **401** `{"detail": "As credenciais de autenticação não foram fornecidas."}`.
- O `access` vale **1 hora** e o `refresh` vale **7 dias** (`SIMPLE_JWT` no `settings.py`).
- Usuário: `contas.Usuario` (login pelo e-mail). Nas FKs, use `settings.AUTH_USER_MODEL`.
- Quem é do grupo é um `grupos.Membro` (`papel`: `organizador` | `jogador`, `posicao`, `nota` de 1 a 10).
  **Atenção:** nas rotas de partida, os jogadores aparecem por `membro_id` (id do `Membro`), não pelo id do usuário.
- Quem **não é membro** do grupo recebe **404** (o grupo "não existe" para ele). Quem é membro mas **não é
  organizador** recebe **403** nas ações de organizador, com `{"detail": "Só o organizador pode …"}`.
- Erros seguem o padrão do DRF: `{"detail": "..."}` ou `{"campo": ["..."]}`. As mensagens estão em português.
- Datas em ISO 8601 com o fuso de São Paulo (`2026-11-12T20:00:00-03:00`). Posições: `GOL`, `ZAG`, `MEI`, `ATA`.
- As listas **não são paginadas**.
- **Rotas que esperam a IA** (alguns segundos): `montar-times`, `POST …/cronica/` e `POST …/narracoes/`.
  O frontend usa timeout de 90 s nelas, e o backend desiste do Gemini em `GEMINI_TIMEOUT_MS` (padrão 20 s).

---

## 1. Contas e grupos (Fernando)

Implementado na PR #49.

### Contas

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| POST | `/api/auth/cadastro/` | `{nome, email, senha, posicao}` | **201** `{usuario, access, refresh}` (já entra logado) |
| POST | `/api/auth/login/` | `{email, password}` | **200** `{refresh, access, usuario}` |
| POST | `/api/auth/refresh/` | `{refresh}` | **200** `{access}` |
| GET | `/api/auth/me/` | — | **200** `{id, nome, email, posicao}` |
| PUT / PATCH | `/api/auth/me/` | `{nome?, posicao?}` | **200** usuário atualizado (`id` e `email` não mudam) |

Regras: o e-mail é guardado em minúsculas e precisa ser único; a `senha` tem no mínimo 8 caracteres e passa
pelos validadores de senha do Django (não pode ser parecida com o nome ou o e-mail, muito comum, nem só números).

```json
// POST /api/auth/cadastro/  {"nome": "Marina", "email": "marina@example.com", "senha": "pelada2026", "posicao": "MEI"}
// 201
{
  "usuario": {"id": 169, "nome": "Marina", "email": "marina@example.com", "posicao": "MEI"},
  "access": "eyJhbGciOiJIUzI1NiIs…",
  "refresh": "eyJhbGciOiJIUzI1NiIs…"
}
// 400 (mesmo e-mail, com letras maiúsculas)
{"email": ["Já existe uma conta com esse e-mail."]}

// POST /api/auth/login/ com a senha errada
// 401
{"detail": "Usuário e/ou senha incorreto(s)"}
```

### Grupos

| Método | Rota | Quem | Corpo | O que faz |
|---|---|---|---|---|
| GET | `/api/grupos/` | logado | — | meus grupos, o mais novo primeiro |
| POST | `/api/grupos/` | logado | `{nome}` (3+ letras) | cria o grupo; quem cria vira **organizador**. **201** |
| GET | `/api/grupos/{id}/` | membros | — | detalhe do grupo |
| GET | `/api/grupos/{id}/membros/` | membros | — | membros com papel, posição e nota |
| POST | `/api/grupos/entrar/` | logado | `{codigo}` | entra pelo código de convite. **201** se entrou agora, **200** se já era membro |

O `codigo` aceita `RACHA-57S`, `racha-57s` ou só `57s`.

```json
// GET /api/grupos/
[
  {"id": 14, "nome": "Pelada de quinta", "codigo_convite": "RACHA-57S", "total_membros": 14,
   "meu_papel": "organizador", "criado_em": "2026-11-19T08:35:21.497703-03:00"}
]

// GET /api/grupos/14/membros/   ("id" é o id do Membro; "usuario_id" é o do Usuario)
[
  {"id": 157, "usuario_id": 155, "nome": "João", "papel": "organizador", "posicao": "ATA", "nota": 9,
   "entrou_em": "2026-11-19T08:35:21.498711-03:00"},
  {"id": 158, "usuario_id": 156, "nome": "Pedro", "papel": "jogador", "posicao": "MEI", "nota": 8,
   "entrou_em": "2026-11-19T08:35:21.499237-03:00"}
  …
]

// POST /api/grupos/entrar/  {"codigo": "RACHA-ZZZ"}
// 400
{"codigo": ["Nenhum grupo com esse código."]}

// GET /api/grupos/14/ por quem não é membro
// 404  (mensagem padrão do Django, em inglês)
{"detail": "No Grupo matches the given query."}
```

---

## 2. Partidas, presença e times (Arthur)

### Status da partida

`aberta` (presença) → `sorteando` (a IA está montando; dura segundos) → `rascunho` (organizador confere) →
`publicada` (o grupo vê os times) → `encerrada` (tem resultado).

### Rotas

| Método | Rota | Quem | Corpo | O que faz |
|---|---|---|---|---|
| GET | `/api/grupos/{id}/partidas/` | membros | — | partidas do grupo (resumo), a mais recente primeiro |
| POST | `/api/grupos/{id}/partidas/` | organizador | ver abaixo | cria a partida. **201** com o detalhe |
| GET | `/api/partidas/{id}/` | membros | — | detalhe: presença, times, explicação da IA, resultado |
| POST | `/api/partidas/{id}/presenca/` | membros | `{vou: true\|false}` | confirma ou desmarca. Devolve o detalhe |
| POST | `/api/partidas/{id}/montar-times/` | organizador | — | a IA monta (ou refaz) os times como **rascunho** |
| POST | `/api/partidas/{id}/confirmar-times/` | organizador | — | publica o rascunho para o grupo |
| POST | `/api/partidas/{id}/trocar/` | organizador | `{jogador_a, jogador_b}` | troca dois jogadores (ids de `Membro`) de times diferentes |

**Criar partida:** `{data_hora, local, num_times, jogadores_por_time, antecedencia_horas}`.
`data_hora` no futuro; `local` com 2+ letras; `num_times` de 2 a 4 (Verde, Preto, Branco, Azul; padrão 2);
`jogadores_por_time` de 2 a 11 (padrão 5); `antecedencia_horas` ∈ {1, 2, 3, 6, 12, 24} (padrão 2) é quando a IA
monta os times sozinha antes do jogo.

**Montagem automática:** abrir a lista de partidas ou o detalhe já dispara o sorteio das partidas `aberta` cuja
hora de sorteio (`sorteio_em`) passou. O comando `python manage.py montar_times_agendados` faz o mesmo (cron).

**Regras e erros (400 `{"detail": …}`):**
- presença só com a partida `aberta` e antes do horário: "Os times já foram montados. Fale com o organizador." /
  "Essa partida já começou.";
- montar times precisa de `num_times × 2` confirmados: "Precisa de pelo menos 4 confirmados para montar 2 times (hoje: 3).";
- confirmar só com `rascunho`: "Não há times aguardando confirmação.";
- trocar só com `rascunho` ou `publicada` ("Só dá para trocar jogadores antes do resultado."); os dois jogadores
  precisam estar em times diferentes desta partida (400 `{"non_field_errors": ["Escolha jogadores de times diferentes."]}`).

**Quem vê o quê no detalhe:** os `times` só aparecem para o grupo depois de `publicada` (o organizador vê o
`rascunho`). A **`nota`** de cada jogador só aparece para o organizador.

```json
// GET /api/grupos/14/partidas/  (resumo)
[
  {"id": 24, "grupo": 14, "data_hora": "2026-11-19T20:00:00-03:00", "local": "Arena Society", "num_times": 2,
   "jogadores_por_time": 5, "antecedencia_horas": 2, "sorteio_em": "2026-11-19T18:00:00-03:00", "vagas": 10,
   "status": "aberta", "total_confirmados": 8, "minha_presenca": "vou", "placar": null},
  {"id": 23, …, "status": "encerrada", "total_confirmados": 10,
   "placar": [{"time_id": 29, "nome": "Verde", "cor": "#15803d", "gols": 5},
              {"time_id": 30, "nome": "Preto", "cor": "#1f2937", "gols": 3}]}
]

// POST /api/partidas/24/montar-times/  (organizador; IA real, 2,9 s)
{
  "id": 24, "grupo": 14, "data_hora": "2026-11-19T20:00:00-03:00", "local": "Arena Society",
  "num_times": 2, "jogadores_por_time": 5, "antecedencia_horas": 2, "sorteio_em": "2026-11-19T18:00:00-03:00",
  "vagas": 10, "status": "rascunho", "total_confirmados": 9, "minha_presenca": "vou", "placar": null,
  "grupo_nome": "Pelada de quinta", "minimo_para_sortear": 4, "eh_organizador": true,
  "confirmados": [{"membro_id": 157, "nome": "João", "posicao": "ATA"}, …],
  "lista_espera": [],
  "nao_vao": [{"membro_id": 169, "nome": "Nina", "posicao": "MEI"}, …],
  "times": [
    {"id": 31, "nome": "Verde", "cor": "#15803d", "forca": 6.8,
     "jogadores": [{"membro_id": 157, "nome": "João", "posicao": "ATA", "nota": 9}, …]},
    {"id": 32, "nome": "Preto", "cor": "#1f2937", "forca": 7.25,
     "jogadores": [{"membro_id": 158, "nome": "Pedro", "posicao": "MEI", "nota": 8}, …]}
  ],
  "diferenca_forca": 0.45,
  "explicacao_ia": "Dividi a pelada pra ninguém reclamar. O Verde veio com o João e o paredão Rafa, enquanto o Preto aposta na dupla Pedro e Caio pra balançar a rede. Vai ser jogo duro e equilibrado!",
  "origem_times": "ia",
  "ajustado_pelo_organizador": false,
  "times_montados_em": "2026-11-19T08:35:29.412408-03:00",
  "times_publicados_em": null,
  "resultado": null
}
```

- `origem_times`: `ia` ou `reserva` (plano B). No plano B a `explicacao_ia` começa com
  "A IA não respondeu, então montei os times pelo plano B: …" e informa a diferença de força.
- Depois de `trocar`, `forca` e `diferenca_forca` são recalculadas e `ajustado_pelo_organizador` vira `true`
  (no exemplo, a troca deixou os dois times com 7,0).
- O detalhe de uma partida `encerrada` traz o `resultado` completo (formato da seção 3).

### Perguntas da Sprint 1 para o Arthur (respondidas pelo código)

1. *Qual o nome do app e dos models?* `partidas.Partida`, `partidas.Presenca` e `partidas.Time`.
2. *Como pego os jogadores de um time?* `time.jogadores.all()` devolve `Membro` (M2M direto).
3. *Pode ter mais de 2 times?* Sim, de 2 a 4. O placar é uma lista com um item por time, e a crônica e o ranking
   aceitam 2 ou mais times (o vencedor é quem fez mais gols; empate no topo = sem vencedor).
4. *Qual `status` indica "times confirmados"?* `publicada`. O resultado pode ser lançado em `publicada`
   ou corrigido em `encerrada`.

---

## 3. Resultado, crônica, ranking e narração

Resultado e gols: Arthur (#36, #37). Crônica, craque, ranking e narração: Gabriel (#39 a #44).

### Modelos (app `resultados`)

```
Resultado      partida (OneToOne, related_name='resultado'), registrado_por, registrado_em (auto_now)
Gol            resultado (FK, related_name='gols'), time (FK partidas.Time), jogador (FK Membro, null = gol
               contra / sem autor), quantidade (1 a 50). O placar é a soma das quantidades por time.
Cronica        resultado (OneToOne, related_name='cronica'), status ok|erro, titulo, texto,
               craque (FK Membro, null), motivo_craque, origem_craque ia|artilheiro|'', erro, gerada_em,
               baseada_em (= registrado_em do resultado usado; se o placar mudar depois, fica desatualizada)
Narracao       partida (FK, related_name='narracoes'), autor (Membro que escreveu), protagonista (Membro que
               fez o lance), lance (relato, até 500), grito, narracao, publicada, criada_em, publicada_em
```

### Resultado (Arthur)

| Método | Rota | Quem | O que faz |
|---|---|---|---|
| GET | `/api/partidas/{id}/resultado/` | membros | placar e gols. **404** "O resultado ainda não foi lançado." |
| PUT | `/api/partidas/{id}/resultado/` | organizador | lança ou corrige o placar; a partida vira `encerrada` |

**Corpo do PUT:** `{"gols": [{"time": 31, "jogador": 157, "quantidade": 2}, {"time": 32, "jogador": null}]}`.
`jogador` é o id do `Membro` (ou `null` para gol contra / sem autor); `quantidade` padrão 1. Cada PUT
**substitui** todos os gols. Lista vazia = 0 x 0. Só com a partida `publicada` ou `encerrada`
("Publique os times antes de lançar o resultado.").

Erros de validação (400 em `gols`): "Um dos gols é de um time que não está nesta partida.",
"Um dos goleadores não joga no time indicado.", "Some os gols do mesmo jogador numa linha só."

```json
// PUT /api/partidas/24/resultado/  (2 do João no Verde; 1 do Gui e 1 sem autor no Preto)
{
  "partida": 24,
  "placar": [{"time_id": 31, "nome": "Verde", "cor": "#15803d", "gols": 2},
             {"time_id": 32, "nome": "Preto", "cor": "#1f2937", "gols": 2}],
  "vencedor": null,
  "gols": [{"id": 77, "time": 31, "jogador": 157, "nome": "João", "quantidade": 2},
           {"id": 78, "time": 32, "jogador": 162, "nome": "Gui", "quantidade": 1},
           {"id": 79, "time": 32, "jogador": null, "nome": "Gol contra / sem autor", "quantidade": 1}],
  "registrado_em": "2026-11-19T08:35:29.501229-03:00"
}
```

Com vencedor, `vencedor` é o item do placar: `{"time_id": 29, "nome": "Verde", "cor": "#15803d", "gols": 5}`.

### Crônica e craque da rodada (Gabriel, #39 e #40)

| Método | Rota | Quem | O que faz |
|---|---|---|---|
| GET | `/api/partidas/{id}/resultado/cronica/` | membros | crônica e craque. **404** sem resultado ou "A crônica ainda não foi gerada." |
| POST | `/api/partidas/{id}/resultado/cronica/` | organizador | a IA escreve (ou reescreve) a crônica e escolhe o craque |

A tela pós-jogo chama o POST logo depois do PUT do resultado (o PUT não espera a IA).

```json
// POST /api/partidas/23/resultado/cronica/  (IA real, 1,7 s)
{
  "status": "ok",
  "titulo": "Caio brilha na noite épica da Pelada de quinta",
  "texto": "A Arena Society tremeu nesta quinta-feira, às 20h, para testemunhar um verdadeiro épico do esporte amador. …\n\nO espetáculo ofensivo teve artilharia pesada … Caio balançou as redes 3 vezes e Pedro contribuiu com 2 gols, enquanto João anotou 2 gols pelo Preto, além de contar com 1 gol sem autor marcado.\n\nO grande destaque da noite foi Caio …",
  "craque": {"membro": 159, "nome": "Caio", "motivo": "Caio foi o craque da rodada por ter marcado 3 gols na vitória do Verde."},
  "origem_craque": "ia",
  "erro": "",
  "gerada_em": "2026-11-19T08:35:31.163995-03:00",
  "desatualizada": false
}
```

- `texto`: 3 parágrafos separados por `\n\n`.
- `desatualizada: true` quando o placar foi corrigido depois da crônica (o organizador gera de novo).
- **Plano B, se a IA falhar:** **200** com `status: "erro"`, `titulo` e `texto` vazios, a mensagem em `erro`
  (ex.: "A IA não respondeu agora. Tente gerar a crônica de novo daqui a alguns minutos.") e o **artilheiro**
  como craque (`origem_craque: "artilheiro"`; empate: time vencedor, depois ordem alfabética; sem gols: `craque: null`).
- **Se já havia uma crônica boa e atualizada** e a nova tentativa falhar, ela é mantida: **503**
  `{"detail": "<mensagem>", "cronica": {…a crônica anterior…}}`.
- Jogador comum no POST: **403** "Só o organizador pode gerar a crônica."

### Ranking do grupo (Gabriel, #42)

`GET /api/grupos/{id}/ranking/` (membros). `jogos` = partidas do grupo com resultado.

```json
{
  "jogos": 2,
  "artilharia": [{"colocacao": 1, "membro": 157, "nome": "João", "gols": 4, "jogos": 2},
                 {"colocacao": 2, "membro": 159, "nome": "Caio", "gols": 3, "jogos": 2}, …],
  "vitorias":   [{"colocacao": 1, "membro": 166, "nome": "Duda", "vitorias": 1, "empates": 0, "derrotas": 0, "jogos": 1},
                 {"colocacao": 1, "membro": 165, "nome": "Leo", "vitorias": 1, "empates": 0, "derrotas": 0, "jogos": 1}, …],
  "craques":    [{"colocacao": 1, "membro": 159, "nome": "Caio", "vezes": 1, "jogos": 2}]
}
```

- Cada lista só traz quem tem o número maior que zero (quem não marcou não entra na artilharia).
- Ordem: número maior primeiro; empate → **menos jogos** primeiro, depois o nome. Empatados no número e nos
  jogos dividem a colocação (1, 2, 2, 4).
- `craques` conta só crônicas atualizadas (uma crônica `desatualizada` não conta) e inclui o craque do plano B.

### Narração do lance e mural (Gabriel, #44)

| Método | Rota | Quem | O que faz |
|---|---|---|---|
| GET | `/api/partidas/{id}/narracoes/` | membros | **mural**: narrações publicadas, a mais nova primeiro |
| POST | `/api/partidas/{id}/narracoes/` | membros | `{lance, protagonista?}` → a IA narra e cria um **rascunho**. **201** |
| POST | `/api/narracoes/{id}/publicar/` | autor | leva o rascunho para o mural |
| DELETE | `/api/narracoes/{id}/` | autor ou organizador | apaga. **204** |

- `lance`: 5 a 500 caracteres. `protagonista`: id do `Membro` que fez o lance; sem ele, é o próprio autor.
  O protagonista precisa ter **jogado** a partida (quem não jogou pode narrar, mas precisa escolher quem fez o lance).
- Só com resultado lançado (**404** antes). O rascunho só aparece para o autor.
- O áudio **não vem da API**: o navegador lê `grito` e `narracao` com a Web Speech API.
- `pode_apagar` diz se quem está vendo pode apagar (autor ou organizador).

```json
// POST /api/partidas/23/narracoes/  (IA real, 1,7 s)
// {"lance": "Arranquei pela esquerda, passei por dois e chutei com tudo... a bola foi parar no telhado do vizinho."}
// 201
{
  "id": 12,
  "lance": "Arranquei pela esquerda, passei por dois e chutei com tudo... a bola foi parar no telhado do vizinho.",
  "grito": "NO TELHADO DO VIZINHO!",
  "narracao": "Lá vai Pedro pela esquerda, arrancando com a bola, passou por dois marcadores com muita velocidade, abriu o espaço e soltou a bomba... chute forte de Pedro... e a bola vai subindo, subindo, e vai parar direto no telhado do vizinho!",
  "autor": {"membro": 158, "nome": "Pedro"},
  "protagonista": {"membro": 158, "nome": "Pedro"},
  "publicada": false,
  "criada_em": "2026-11-19T08:35:32.832156-03:00",
  "publicada_em": null,
  "pode_apagar": true
}
// POST /api/narracoes/12/publicar/ → o mesmo objeto com "publicada": true e "publicada_em" preenchido
```

| Status | Quando | `detail` |
|---|---|---|
| 400 | `lance` vazio, curto ou longo; protagonista que não jogou | `{"lance": […]}` / `{"protagonista": […]}` |
| 403 | publicar narração de outro / apagar sem ser autor nem organizador | "Só quem narrou pode publicar." / "Só quem narrou ou o organizador pode apagar." |
| 404 | partida sem resultado; rascunho de outra pessoa | "O resultado ainda não foi lançado." / "Narração não encontrada." |
| 422 | a IA achou que não é um lance de futebol (ou é ofensivo) | "Não deu para narrar: descreva uma jogada da partida." |
| 429 | 10 narrações geradas por esse membro nesta partida | "Você já gerou 10 narrações nesta partida." |
| 503 | a IA não respondeu (nada é salvo; tentar de novo) | "A IA não respondeu agora. Tente gerar a narração de novo daqui a pouco." |

---

## 4. Módulo de IA compartilhado (`backend/ia/`)

Todas as chamadas ao Gemini passam por `ia/gemini.py` (do Arthur; substituiu o `ia/cliente.py` da proposta
original, removido no #39). Configuração no `backend/.env`:

| Variável | Padrão | Para quê |
|---|---|---|
| `GEMINI_API_KEY` | vazio | chave do Google AI Studio. Sem ela, sorteio e crônica usam os planos B e a narração responde 503 |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | modelo (o `gemini-2.5-flash` devolve 404 para chaves novas) |
| `GEMINI_TIMEOUT_MS` | `20000` | tempo máximo de cada chamada |

```python
from ia import gemini

try:
    dados = gemini.gerar_json(prompt, json_schema=SCHEMA, instrucoes=INSTRUCAO, temperatura=1.0)  # dict
except gemini.IAIndisponivel:   # sem chave, sem rede, timeout, cota, erro do Google
    ...                         # plano B
except gemini.RespostaInvalida: # respondeu, mas não é o JSON pedido
    ...
```

Quem usa: `partidas/sorteio.py` (times), `ia/cronica.py` (crônica e craque) e `ia/narracao.py` (narração).
Cada um valida a resposta da IA no código antes de salvar. `python manage.py testar_gemini [--cronica]`
testa a chave e o modelo.

**Nos testes**, simule a IA com `mock.patch('ia.gemini.gerar_json')` (todo o código chama pelo módulo, então
um mock cobre sorteio, crônica e narração). Nenhum teste chama o Gemini de verdade.
