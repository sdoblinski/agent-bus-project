# AgentBus — Barramento de Agentes (demo)

Projeto demonstrativo de um barramento leve para comunicação entre agentes. Inclui:
- `bus.py` (FastAPI) — servidor do barramento;
- `worker_agent.py` — agente meteorologista que usa MCP + Google GenAI;
- `interface_agent.py` — cliente de chat simples para interação humana.


[Conheça os detalhes de arquitetura aqui.](ARCHITECTURE.md)


**Comandos (tool.taskipy)**:
- `task dev` : sobe toda a infraestrutura (equivalente a `honcho start`).
- `task chat`: roda `python interface_agent.py` (abre o chat de atendimento).
- `task bus` : roda `python bus.py` (inicia o servidor do barramento na porta 8000).
- `task worker`: roda `python worker_agent.py` (inicia o agente worker).

**Stack (resumido)**:
- Python >= 3.11
- FastAPI + Uvicorn
- Pydantic
- MCP (mcp) para exposição de ferramentas ao LLM
- Google GenAI (Gemini) via `google-genai`
- httpx, honcho, taskipy

**Instalação rápida**:
1. Tenha Python 3.11+ instalado.
2. Crie e ative um virtualenv:

	python -m venv .venv
	source .venv/bin/activate

3. Recomendado: use o gerenciador `uv` para instalar e executar dependências.

   - Instalação (Mac / Linux) via `curl`:

	   curl -LsSf https://astral.sh/uv/install.sh | sh

   - Instalação (Windows) via PowerShell:

	   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   - Após instalar o `uv`, instale as dependências do projeto:

	   uv install .

   - (Opcional) instalar ferramentas de desenvolvimento:

	   uv install honcho taskipy

   Observação: `uv` é um gerenciador/launcher utilizado neste projeto para ações como `uv run`.

4. Configure a chave do Gemini (necessária para o `worker_agent`):

	export GEMINI_API_KEY="sua_chave_aqui"
