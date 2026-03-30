# AgentBus — Barramento de Agentes (demo)

Projeto demonstrativo de um barramento leve para comunicação entre agentes. Inclui:
- `bus.py` (FastAPI) — servidor do barramento;
- `worker_agent.py` — agente meteorologista que usa MCP + Google GenAI;
- `interface_agent.py` — cliente de chat simples para interação humana.

[Conheça os detalhes de arquitetura aqui.](ARCHITECTURE.md)

**Stack (resumo)**:
- Python >= 3.11
- FastAPI + Uvicorn + Pydantic
- MCP (Model Context Protocol) para exposição de ferramentas ao LLM
- Google GenAI (Gemini) via `google-genai`
- Infra local: `uv`, `honcho`, `taskipy`, `python-dotenv`

---

## 🚀 Instalação Rápida

Para garantir consistência e velocidade, este projeto utiliza o **`uv`** como gerenciador universal de pacotes e versões do Python.

**1. Instale o gerenciador `uv` na sua máquina:**
- Mac / Linux:
  curl -LsSf https://astral.sh/uv/install.sh | sh

- Windows (PowerShell):
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

*(Nota: O `uv` gerenciará a versão do Python automaticamente, você não precisa instalá-lo manualmente).*

**2. Instale as dependências do projeto:**
Na raiz do projeto, execute o comando abaixo. Ele criará o ambiente virtual isolado (`.venv`) e instalará todas as bibliotecas necessárias em segundos:

uv sync


**3. Configure as Variáveis de Ambiente:**
O agente (`worker_agent`) requer acesso à API do Gemini. 
- Crie um arquivo chamado **exatamente** `.env` na raiz do projeto.
- Adicione a sua chave dentro dele:

GEMINI_API_KEY=sua_chave_aqui


---

## 💻 Como Executar (Comandos `taskipy`)

Nós utilizamos atalhos para facilitar a inicialização. Execute os comandos abaixo sempre precedidos de `uv run` para garantir que rodem dentro do ambiente isolado.

Abra **dois terminais** na raiz do projeto:

**Terminal 1 (Sobe a Infraestrutura e os Agentes):**
uv run task dev
*(Este comando utiliza o `honcho` para rodar o `bus.py` e o `worker_agent.py` simultaneamente).*

**Terminal 2 (Abre a Interface com o Usuário):**
uv run task chat


### Comandos Individuais (Para Debug)
Caso precise debugar algum componente isoladamente, você pode rodar:
- `uv run task bus` : Inicia apenas o servidor REST do barramento na porta 8000.
- `uv run task worker` : Inicia apenas o agente especialista e conecta ao MCP local.