# Projeto3-Tecweb-Racha

**Link do fluxo de telas:**
https://claude.ai/artifact/4ciMLDKPG57tMksqT6iQkD

## Como rodar

**Backend** (Django + DRF, porta 8000)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows (no Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # ajuste os valores
python manage.py migrate
python manage.py popular_racha # dados de exemplo (veja abaixo)
python manage.py runserver
python manage.py test          # todos os testes (a IA e simulada, nao precisa de chave)
```

**Chave do Gemini:** crie uma chave gratuita em https://aistudio.google.com/apikey e coloque em
`GEMINI_API_KEY` no `backend/.env`. Sem chave o app funciona igual, mas o sorteio usa o plano B
(algoritmo) e avisa isso na explicacao.

**Dados de exemplo** (`python manage.py popular_racha`): 14 jogadores, o grupo "Pelada de quinta",
uma partida ja jogada (Verde 5 x 3 Preto) e a proxima quinta com 8 de 10 confirmados.
Organizador: `joao@example.com` · jogador comum: `pedro@example.com` · senha de todos: `racha1234`.
Rodar de novo apaga e recria so esses dados.

**Frontend** (Vite + React + Tailwind, porta 5173)

```bash
cd frontend
npm install
copy .env.example .env         # VITE_API_URL=http://localhost:8000/api
npm run dev
```

## API (contas e grupos)

| Metodo | Rota | O que faz |
|---|---|---|
| POST | `/api/auth/cadastro/` | cria conta `{nome, email, senha, posicao}` e devolve `{usuario, access, refresh}` |
| POST | `/api/auth/login/` | `{email, password}` → `{access, refresh, usuario}` |
| POST | `/api/auth/refresh/` | `{refresh}` → `{access}` |
| GET/PATCH | `/api/auth/me/` | usuario logado |
| GET | `/api/grupos/` | meus grupos |
| POST | `/api/grupos/` | cria grupo `{nome}` (quem cria vira organizador) |
| GET | `/api/grupos/{id}/` | detalhe do grupo (so membros) |
| GET | `/api/grupos/{id}/membros/` | membros com posicao e nota |
| POST | `/api/grupos/entrar/` | entra com `{codigo}` (ex.: `RACHA-7K2`) |

Todas as rotas, exceto cadastro/login/refresh, pedem `Authorization: Bearer <access>`.
O usuario customizado e `contas.Usuario` (`settings.AUTH_USER_MODEL`): use `settings.AUTH_USER_MODEL` nas FKs das outras partes.

## API (partidas, presenca, sorteio e resultado)

| Metodo | Rota | O que faz |
|---|---|---|
| GET | `/api/grupos/{id}/partidas/` | partidas do grupo (com total de confirmados, minha presenca e placar) |
| POST | `/api/grupos/{id}/partidas/` | cria partida `{data_hora, local, num_times, jogadores_por_time, antecedencia_horas}` (organizador) |
| GET | `/api/partidas/{id}/` | detalhe: confirmados, lista de espera, times, explicacao da IA, resultado |
| POST | `/api/partidas/{id}/presenca/` | `{vou: true\|false}` |
| POST | `/api/partidas/{id}/montar-times/` | IA monta (ou refaz) os times como rascunho (organizador) |
| POST | `/api/partidas/{id}/confirmar-times/` | publica o rascunho para o grupo (organizador) |
| POST | `/api/partidas/{id}/trocar/` | `{jogador_a, jogador_b}` troca dois jogadores de time (organizador) |
| GET/PUT | `/api/partidas/{id}/resultado/` | placar; PUT `{gols: [{time, jogador\|null, quantidade}]}` (organizador) |

Status da partida: `aberta` (presenca) → `rascunho` (organizador confere) → `publicada` → `encerrada` (com resultado).

## Como a IA monta os times

1. Os primeiros confirmados ocupam as vagas (`num_times x jogadores_por_time`); o resto vai para a lista de espera.
2. O backend manda para o Gemini os jogadores (id, nome, posicao, nota) e pede, em **modo JSON**,
   os times + uma explicacao curta que **nao revela as notas** (ela aparece para todo o grupo).
3. **O codigo valida a resposta** (`partidas/equilibrio.py`): todo mundo uma vez so, tamanhos iguais,
   goleiros separados e diferenca de forca (media das notas) dentro do limite.
4. Se a resposta for recusada, os erros voltam para a IA e ela tenta mais uma vez.
5. Se a IA errar de novo ou estiver fora do ar, entra o **plano B**: um algoritmo em zigue-zague
   com trocas, e a explicacao avisa isso. O sorteio nunca trava por causa da IA.

**Montagem automatica:** no horario definido (padrao 2h antes do jogo) a IA monta e publica os times.
Isso acontece quando alguem abre a partida ou a lista do grupo, e tambem pelo comando
`python manage.py montar_times_agendados` (para um cron no deploy, ex.: a cada 10 min).
