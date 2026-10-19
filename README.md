# Etermory

> *Memórias que permanecem.*

Rede social de memórias em que cada lembrança é uma **Polaroid**: foto, legenda, data, emoções, estado da memória, música e local, com privacidade definida em cada Polaroid.

Projeto acadêmico em **Python 3.12 + Flask 3 + SQLAlchemy 2 + PostgreSQL**, com foco em Programação Orientada a Objetos.

## Como rodar localmente

### 1. Pré-requisitos

- Python 3.12 ou mais novo
- Git
- PostgreSQL 16 ou mais novo (opcional no desenvolvimento: sem ele, o projeto usa SQLite em `instance/etermory.db`)

### 2. Instalar

```bash
git clone https://github.com/Ardyson25/etemory.git etermory
cd etermory
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # no Windows: copy .env.example .env
```

Edite o `.env` e troque o `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Criar o banco e rodar

```bash
flask --app wsgi db upgrade      # cria as tabelas pelas migrações
flask --app wsgi run --debug     # abre em http://127.0.0.1:5000
```

Teste rápido: abra `http://127.0.0.1:5000/saude`. A resposta esperada é `{"instancia":"local","status":"ok"}`.

### 4. Testes

```bash
pytest                               # roda todos os testes
pytest --cov=app --cov-report=term   # com cobertura
```

Os testes usam SQLite em memória e não precisam de PostgreSQL.

## Comandos úteis

| Comando | O que faz |
|---|---|
| `flask --app wsgi db migrate -m "mensagem"` | Gera uma migração depois de mudar um modelo |
| `flask --app wsgi db upgrade` | Aplica as migrações |
| `flask --app wsgi limpar-lixeira` | Apaga de vez as memórias com 30 dias ou mais na Lixeira (RN14) |
| `flask --app wsgi routes` | Lista todas as rotas |
| `gunicorn -c gunicorn.conf.py wsgi:app` | Roda em produção (Linux) |

## Estrutura

```
app/
├── __init__.py        # create_app(): app factory
├── config.py          # configurações por ambiente
├── extensions.py      # db, login_manager, migrate, csrf
├── domain/            # POO pura: enums, regras de visibilidade e de comentário, notificações
├── models/            # modelos SQLAlchemy (tabelas)
├── repositories/      # consultas ao banco
├── services/          # regras de negócio
├── forms/             # formulários Flask-WTF (CSRF)
├── routes/            # blueprints: auth, timeline, polaroids, perfil, albuns, notificacoes, saude
├── templates/         # telas em Jinja2
└── static/            # css, js, icons
tests/                 # unit/ e integration/
migrations/            # migrações do banco (Alembic)
docs/                  # documentação V1 a V4, diagramas e evidências
```

## Publicação online (Fase 3)

Render (aplicação) + Neon (PostgreSQL), configurados pelo [render.yaml](render.yaml). Passo a passo na seção 25 da [Documentação V3](docs/documentacao_v3.md).

No Render, as fotos ficam no banco (`ARMAZENAMENTO=banco`), porque o disco do plano gratuito é apagado a cada reinício.

## Infraestrutura própria (Fase 4)

4 VMs Ubuntu Server 24.04 no VirtualBox: `vm-proxy` (Nginx com failover), `vm-app1` e `vm-app2` (Gunicorn + Flask) e `vm-db` (PostgreSQL, NFS e backups).

- Configurações: [deploy/](deploy/)
- Scripts: [scripts/](scripts/)
- Montagem: [scripts/provisionar/](scripts/provisionar/), na ordem da seção 29 da [Documentação V4](docs/documentacao_v4.md)

```bash
git push producao main                      # deploy de uma instância por vez, sem parar o site
./scripts/teste_failover.sh                 # mostra app1/app2 alternando e as falhas
sudo etermory-backup                        # (vm-db) backup na hora
```

## Documentação

- [Documentação V1 — Planejamento](docs/documentacao_v1.md)
- [Documentação V2 — Desenvolvimento](docs/documentacao_v2.md)
- [Documentação V3 — Implantação](docs/documentacao_v3.md)
- [Documentação V4 — Infraestrutura](docs/documentacao_v4.md)
- [Documentação Final](docs/documentacao_final.md) — teste de indisponibilidade, lições aprendidas e rastreabilidade do enunciado
- [Roteiro da apresentação](docs/apresentacao/roteiro_apresentacao.md)

## Teste de indisponibilidade (Fase 5)

```bash
./scripts/teste_indisponibilidade.sh http://192.168.56.10/saude
```

O script guia os passos (derrubar a app1, conferir o site, religar, restaurar o backup), registra o horário de cada um e salva as evidências em `docs/evidencias/teste_indisponibilidade/`.
