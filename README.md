# AgentBus — Barramento de Agentes (demo)

Projeto demonstrativo de um barramento de eventos robusto para comunicação assíncrona entre agentes. Inclui:
- `bus.py` (FastAPI + RabbitMQ) — Orquestrador do barramento e infraestrutura de mensageria;
- `worker_agent.py` — Agente meteorologista com memória cognitiva (ChromaDB) e processamento via Gemini 3 Flash;
- `mcp_server.py` — Servidor MCP (Model Context Protocol) que expõe ferramentas de clima real;
- `interface_agent.py` — Cliente de chat em tempo real com suporte a múltiplos IDs de usuário.

## 📄 Documentação técnica
- [Arquitetura do sistema](docs/ARCHITECTURE.md)
- [Memória Cognitiva e RAG](docs/COGNITIVEMEMORY.md)

## 🔧 Stack
- **Linguagem:** Python >= 3.11
- **Mensageria:** RabbitMQ (via `aio-pika`)
- **API/Bus:** FastAPI (Lifespan pattern) + Uvicorn
- **Inteligência:** Google GenAI (Gemini 3 Flash)
- **Ferramentas:** MCP (Model Context Protocol) para Stdio transport
- **Banco Vetorial:** ChromaDB (Persistência de fatos do usuário)
- **Gerenciamento:** `uv`, `honcho`, `taskipy`, `python-dotenv`

---

## 🚀 Instalação Rápida

Este projeto utiliza o **`uv`** para gerenciamento de pacotes e o **RabbitMQ** como motor de mensageria.

**1. Pré-requisito (RabbitMQ):**
Certifique-se de ter o RabbitMQ rodando localmente (porta 5672 para AMQP e 15672 para o Painel).
*Dica: `docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management`*

**2. Instale o gerenciador `uv`:**
- Mac / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

**3. Instale as dependências:**
```bash
uv sync
```

**4. Configure as Variáveis de Ambiente:**
Crie um arquivo `.env` na raiz do projeto com sua chave:
```env
GEMINI_API_KEY=sua_chave_aqui
```

---

## 💻 Como Executar (Comandos `taskipy`)

Abra **dois terminais** na raiz do projeto para rodar o sistema completo:

**Terminal 1 (Infraestrutura e Agentes):**
```bash
uv run task dev
```
*(Inicia o `bus.py` e o `worker_agent.py`. O worker inicializará automaticamente o `mcp_server.py` via Stdio).*

**Terminal 2 (Interface de Chat):**
```bash
uv run task chat
```
*(Você pode abrir este terminal múltiplas vezes; cada instância gerará um `USER_ID` único e o RabbitMQ isolará as conversas).*

### Comandos de Debug
- `uv run task bus` : Inicia apenas o servidor do barramento e configura as filas no RabbitMQ.
- `uv run task worker` : Inicia o agente meteorologista e o conecta ao servidor de ferramentas MCP.
- `npx @modelcontextprotocol/inspector uv run python mcp_server.py` : Testa isoladamente o servidor de clima.