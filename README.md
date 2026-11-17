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
python manage.py runserver
python manage.py test          # testes de contas e grupos
```

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
