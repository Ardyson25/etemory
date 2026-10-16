# Etermory — Roteiro da apresentação

> Duração planejada: **20 minutos + perguntas**. Se o professor der outro tempo, mantenha a proporção de cada bloco.
> Os nomes vêm da tabela de papéis da documentação: [PREENCHER] em cada bloco.

## Visão geral

| # | Bloco | Quem (papel) | Tempo | Acumulado |
|---|---|---|---|---|
| 1 | Abertura: problema, produto e escopo | Product Owner | 2:00 | 2:00 |
| 2 | Como trabalhamos: Scrum, Git e CI | Scrum Master | 2:00 | 4:00 |
| 3 | **Demonstração ao vivo do produto** | Front-end | 3:00 | 7:00 |
| 4 | **POO no código** | Back-end 1 | 3:30 | 10:30 |
| 5 | Arquitetura, banco e publicação online | Back-end 2 | 2:30 | 13:00 |
| 6 | Testes e qualidade | QA | 2:00 | 15:00 |
| 7 | **Infraestrutura e teste de failover ao vivo** | Infraestrutura | 4:00 | 19:00 |
| 8 | Lições aprendidas e encerramento | Product Owner | 1:00 | 20:00 |
| — | Perguntas | Todos (quem respondeu a parte) | — | — |

Cada integrante fala da parte que **fez e documentou**, e isso confere com o histórico do Git.

---

## Preparação (no dia anterior e 30 min antes)

- [ ] As 4 VMs ligadas e `etermory-healthcheck` com tudo OK.
- [ ] Dados de exemplo no ambiente das VMs: 3 contas, Polaroids, um álbum. Use `scripts/popular_demo.py` apontando para o banco da vm-db, ou crie à mão.
- [ ] Navegador com duas janelas: normal logada como `ana`, anônima logada como `bia`.
- [ ] Terminais abertos e com fonte grande:
  - T1: `./scripts/teste_failover.sh http://192.168.56.10/saude 0.5 600`
  - T2: SSH na vm-app1
  - T3: SSH na vm-proxy com `sudo tail -f /var/log/nginx/etermory_error.log`
- [ ] VS Code aberto em `app/domain/visibilidade.py`, com o zoom aumentado.
- [ ] Diagramas abertos: classes (seção 10.2/10.3), arquitetura das VMs (27.3) e DER (23.1).
- [ ] Site do Render aberto **5 minutos antes** (ele dorme após 15 min sem acesso e leva ~1 min para acordar).
- [ ] **Plano B:** vídeo gravado do teste de failover e da restauração, e prints em `docs/evidencias/`. Se algo falhar ao vivo, mostra o vídeo e segue.

---

## 1. Abertura — Product Owner (2:00)

**Slide:** logo Etermory, "Memórias que permanecem".

> "Redes sociais tratam memórias como conteúdo descartável: some no feed em horas e a privacidade é da conta inteira. O Etermory é uma rede social de memórias. Cada lembrança é uma **Polaroid** com foto, legenda, data, até 3 emoções, estado da memória, música e local, e **cada Polaroid tem sua própria privacidade**."

- Identidade de "clínica de memórias": Registro de Memória, Prontuário, Vínculos, Arquivo e Lixeira.
- Ponto de partida: a v3.7.6 (HTML/JS + Firebase) **não tinha back-end próprio**. Refizemos todo o back-end em Python com POO.
- **Escopo:** 9 blocos essenciais entregues. Ficou de fora o que depende de tempo real ou de mídia pesada (chat, stories, vídeo), porque complica o failover e não acrescenta POO.

**Passa para:** "Para entregar isso em 7 pessoas, a gente se organizou assim..."

## 2. Como trabalhamos — Scrum Master (2:00)

**Slide:** quadro do GitHub Projects + gráfico de contribuidores do GitHub.

- 7 sprints de 2 semanas, uma ou duas por fase; backlog com 42 itens em story points.
- Uma branch por item → pull request → 1 revisão + **CI verde** → merge na `main`.
- Commits no padrão `feat(polaroids): ... (RF07)`, ligados aos requisitos.
- O CI roda os testes em todo PR e **bloqueia se a cobertura cair abaixo de 80%**.
- Mostrar: `git log --oneline --graph | head -20` e *Insights → Contributors*.

## 3. Demonstração ao vivo — Front-end (3:00)

Roteiro, em `https://192.168.56.10`:

1. **(ana)** Nova memória: foto, legenda com `@bia`, 2 emoções, música com link do Spotify, visibilidade **Melhores amigos** → *Registrar memória*.
2. **(bia, janela anônima)** Recarregar a página: o sino mostra a **menção**. Abrir a Polaroid, **curtir** (o contador sobe sem recarregar) e **comentar**.
3. **(ana)** Notificações: curtida e comentário. Em *Melhores amigos*, desmarcar a bia.
4. **(bia)** Recarregar a Polaroid: **404**. Ela perdeu o acesso na hora (RN05).
5. **(ana)** Excluir uma Polaroid → **Lixeira** com "30 dias restantes" → Restaurar.
6. Alternar o **tema escuro** (◐).

> Frase de transição: "Por trás de 'a bia deixou de ver', tem uma regra de negócio implementada com polimorfismo. Ela vai mostrar."

## 4. POO no código — Back-end 1 (3:30)

**Tela:** VS Code + diagrama de classes 10.3.

1. **Abstração e polimorfismo** (`app/domain/visibilidade.py`, `politica_acesso.py`):
   > "`RegraVisibilidade` é uma classe abstrata: diz que toda regra responde `pode_ver`, mas não diz como. As 4 subclasses respondem cada uma do seu jeito. A `PoliticaAcesso` pede a regra para a fábrica e chama `pode_ver` sem saber qual recebeu: não existe nenhum `if visibilidade == ...`. Para criar uma visibilidade nova, basta uma classe nova."
2. **Herança** (`app/models/notificacao.py`): 6 tipos de notificação herdam de `Notificacao`. Uma tabela só, com a coluna `tipo`. A tela chama `n.texto()` e cada subclasse responde o seu texto.
3. **Encapsulamento** (`app/models/polaroid.py`): `status` não tem setter. Só muda por `arquivar()`, `mover_para_lixeira()` e `restaurar()`, que validam a transição. A senha só existe como hash.
4. **Composição × agregação:** apagar a Polaroid apaga fotos, curtidas e comentários (composição); apagar o álbum mantém as Polaroids (agregação).
5. **Bônus:** `Armazenamento` (disco × banco) é o mesmo padrão, usado para resolver a publicação no Render.

## 5. Arquitetura, banco e publicação — Back-end 2 (2:30)

**Slides:** diagrama de camadas (10.6) e DER (23.1).

- Camadas: **rota fina → serviço (regras) → domínio + repositório → modelo → banco**.
- 11 tabelas no PostgreSQL com FKs, `UNIQUE`, `CHECK` e `CASCADE`; migrações versionadas.
- **Diferença do Firestore:** antes as listas de seguidores e "quem pode ver" eram copiadas em cada documento. Agora a permissão é **calculada por consulta**, sem cópias desatualizadas.
- Segurança: hash de senha, CSRF em todo formulário, upload validado pelo conteúdo, `https://` obrigatório nos links e a foto privada protegida até pela URL.
- Publicação: **Render + Neon** (mostrar a URL pública e o `/saude`). Problema encontrado: o disco do Render é apagado a cada reinício. Solução: as fotos vão para o banco.

## 6. Testes — QA (2:00)

**Tela:** terminal com `pytest --cov=app`.

- **114 testes, 92% de cobertura** (99% no domínio). Cada teste leva o nome da regra: `test_rn07_...`.
- Destaque: `test_sql_e_politica_concordam_em_todos_os_casos`. A regra de visibilidade existe em Python e em SQL (timeline); o teste cria 30 Polaroids × 4 leitores e garante que as duas respostas são iguais.
- Mostrar a tabela de casos de teste (seção 19.1) e os bugs encontrados (seção 20).

## 7. Infraestrutura e failover ao vivo — Infraestrutura (4:00)

**Slide:** arquitetura das VMs (27.3). Falar por 40 s: 4 VMs Ubuntu 24.04, ufw bloqueando tudo, usuário de serviço sem login, systemd, backup diário com cópia em outra máquina.

**Ao vivo (T1 visível o tempo todo):**

1. T1 mostra `/saude` alternando **app1, app2, app1, app2...**
2. T2: `sudo systemctl stop etermory` na vm-app1.
   > "A app1 caiu. Olhem o T1: só a app2 responde, e **nenhuma falha**."
3. T3: o error.log do Nginx mostra `connect() failed (111: Connection refused) ... upstream: "http://192.168.56.11:8000/..."`.
4. Navegador: a bia continua logada e navegando. A sessão vale nas duas instâncias porque elas usam a mesma `SECRET_KEY`, e as fotos estão no NFS.
5. T2: `sudo systemctl start etermory`. Em até 15 s a app1 **volta** ao T1.
6. **(Se der tempo, senão vídeo)** desligar a VM inteira pelo VirtualBox: aparecem respostas "lentas" de ~2 s (o `proxy_connect_timeout`), mas sem falha.
7. Backup e restauração: **vídeo de 30 s** ou números da seção 40.2: "apagamos todas as Polaroids, restauramos o backup em **[N] segundos** e voltou tudo".

> Fechamento: "No teste completo, o tempo de indisponibilidade com a app1 fora foi de **[PREENCHER] segundos**."

## 8. Encerramento — Product Owner (1:00)

- 2 ou 3 lições aprendidas (seção 46 da documentação final).
- "O código, os testes e a documentação V1 a V4 + final estão no repositório. Obrigado." → perguntas.

---

## Perguntas prováveis (e quem responde)

| Pergunta | Resposta curta | Quem |
|---|---|---|
| "Onde está o polimorfismo?" | `PoliticaAcesso.pode_ver` chama `regra.pode_ver()` sem saber a subclasse; `n.texto()` nas notificações; `Armazenamento.salvar()` | Back-end 1 |
| "Por que Flask e não Django?" | Mais simples para iniciantes e deixa as classes de POO explícitas; os blueprints dividem o trabalho (decisão D01) | Back-end 2 |
| "E se o Nginx cair?" | O site cai: é ponto único de falha. Mitigação: systemd reinicia; o opcional seria keepalived com IP virtual (seção 39.4) | Infraestrutura |
| "E se o banco cair?" | Site com erro; recuperação pelo backup testado. O opcional seria uma réplica do PostgreSQL | Infraestrutura |
| "Por que o login não cai ao trocar de instância?" | A sessão é um cookie assinado; com a mesma `SECRET_KEY` nas duas, qualquer uma valida | Infraestrutura |
| "Como garantem que a timeline não mostra o que não devia?" | Teste que compara SQL com a regra em Python em todas as combinações | QA |
| "Deploy derruba o site?" | Não: `deploy.sh` atualiza uma instância por vez, com rollback automático se não subir | Scrum Master / Infraestrutura |
| "Por que fotos no banco no Render?" | O disco do plano gratuito é apagado a cada reinício; nas VMs ficam em disco/NFS | Back-end 2 |
| "O que a IA fez?" | Mentor técnico e base inicial do código; tudo revisado e testado pelo grupo (seção 14.5) | Product Owner |
