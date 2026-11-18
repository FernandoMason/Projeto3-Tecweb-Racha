# Projeto3-Tecweb-Racha

## Cronograma

Duas sprints, conforme o enunciado. Cada item corresponde a uma issue do quadro (GitHub Projects), com o responsável.
Apresentação e entrega final: **24/11/2026** (commits até 09:30).

### Sprint 1 · 10/11 a 13/11

**Entrega:** proposta validada, fluxo de telas e quadro prontos; cadastro e login; criar e entrar em grupos com código de convite; criar partida e confirmar presença; cliente do Gemini no backend; registrar o resultado da partida (placar e autores dos gols).

- [x] #1 Definir proposta do projeto (Fernando, Arthur, Gabriel)
- [x] #2 Validar proposta com a professora (Fernando, Arthur, Gabriel)
- [ ] #3 Criar repositório no GitHub (Fernando)
- [x] #4 Criar quadro de tarefas (Gabriel)
- [ ] #5 Desenhar fluxo de telas (Arthur)
- [x] #6 Escrever cronograma no README (Gabriel)
- [ ] #7 Combinar contrato da API (Fernando, Arthur, Gabriel)
- [ ] #8 Setup do backend (Fernando)
- [ ] #9 Setup do frontend (Fernando)
- [ ] #10 Layout base e componentes (Fernando)
- [ ] #11 API de cadastro e login (Fernando)
- [ ] #12 Telas de início, login e cadastro (Fernando)
- [ ] #13 Modelos Grupo e Membro (Fernando)
- [ ] #14 API de grupos (Fernando)
- [ ] #15 Telas de grupos (Fernando)
- [ ] #21 Modelos Partida, Presença e Time (Arthur)
- [ ] #22 API de partidas (Arthur)
- [ ] #23 API de presença (Arthur)
- [ ] #24 Tela de nova partida (Arthur)
- [ ] #25 Tela da partida (Arthur)
- [ ] #26 Dados de teste (seed) (Arthur)
- [ ] #34 Configurar o Gemini (Gabriel)
- [x] #35 Cliente do Gemini (Gabriel)
- [ ] #36 Modelos Resultado e Gol (Gabriel)
- [ ] #37 API de resultado (Gabriel)
- [ ] #38 Tela de resultado (Gabriel)

### Sprint 2 · 16/11 a 19/11

**Entrega:** organizador edita notas e posições; times montados pela IA (automaticamente antes do jogo), com validação de equilíbrio e ajuste manual; crônica da rodada e craque escritos pela IA; ranking do grupo; narração de lances com texto e áudio (diferencial); deploy público; teste com usuários reais e ajustes.

- [ ] #16 Gestão de membros (Fernando)
- [ ] #17 Deploy do backend (Fernando)
- [ ] #18 Deploy do frontend (Fernando)
- [ ] #19 Testes de contas e grupos (Fernando)
- [ ] #20 Polimento geral da interface (Fernando)
- [ ] #27 Prompt do sorteio de times (Arthur)
- [ ] #28 Validação de equilíbrio (Arthur)
- [ ] #29 Montagem automática dos times (Arthur)
- [ ] #30 Tela de sorteio (Arthur)
- [ ] #31 Ajuste manual dos times (Arthur)
- [ ] #32 Testes de partidas e sorteio (Arthur)
- [ ] #33 Melhorar prompt pelo feedback (Arthur)
- [ ] #39 Prompt da crônica e do craque (Gabriel)
- [ ] #40 Endpoint da crônica (Gabriel)
- [ ] #41 Tela pós-jogo (Gabriel)
- [ ] #42 API de ranking (Gabriel)
- [ ] #43 Tela de ranking (Gabriel)
- [ ] #44 Narração do lance, diferencial (Gabriel)
- [ ] #45 README final (Gabriel)
- [ ] #46 Teste com usuários (Fernando, Arthur, Gabriel)
- [ ] #47 Ajustes a partir do feedback (Fernando, Arthur, Gabriel)

### Apresentação · 20/11 a 24/11

- [ ] #48 Preparar apresentação (Fernando, Arthur, Gabriel)

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
