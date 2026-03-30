# worker_agent.py
import asyncio
import httpx
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai

from dotenv import load_dotenv
load_dotenv()

# Configurações da nossa arquitetura
BUS_URL = "http://localhost:8000"
MODEL_ID = "gemini-2.5-flash"

# Inicializa o cliente do Gemini (ele busca a GEMINI_API_KEY nas variáveis de ambiente automaticamente)
ai_client = genai.Client()

async def main():
    print("🌤️ Iniciando Agente Meteorologista (com Inteligência Gemini)...")
    
    # 1. Configura a conexão com o Servidor MCP local
    server_params = StdioServerParameters(command="uv", args=["run", "python", "mcp_server.py"])
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[MCP] Conectado às ferramentas com sucesso!")
            
            async with httpx.AsyncClient() as http_client:
                print("[BUS] Aguardando tarefas no barramento...")
                while True:
                    try:
                        # Faz o polling no AgentBus
                        response = await http_client.get(f"{BUS_URL}/poll/meteorologista")
                        messages = response.json()
                        
                        for msg in messages:
                            user_text = msg['content']
                            print(f"\n📩 [Nova Tarefa de {msg['sender']}]: {user_text}")
                            
                            # ==========================================================
                            # PASSO 1: O CÉREBRO PENSA E DECIDE (Raciocínio)
                            # ==========================================================
                            print("🧠 [LLM] Analisando a intenção do usuário...")
                            prompt_extracao = f"""
                            Você é o cérebro de um agente de clima. O usuário disse: "{user_text}"
                            Se o usuário mencionou o nome de uma cidade, responda APENAS com o nome da cidade e nada mais.
                            Se não houver o nome de uma cidade na frase, responda APENAS com a palavra 'NENHUMA'.
                            """
                            resposta_extracao = ai_client.models.generate_content(
                                model=MODEL_ID, contents=prompt_extracao
                            )
                            cidade = resposta_extracao.text.strip()
                            
                            if cidade != "NENHUMA":
                                # ==========================================================
                                # PASSO 2: O AGENTE AGE (Acionando o MCP)
                                # ==========================================================
                                print(f"🛠️ [Ação] Cidade identificada: {cidade}. Consultando Servidor MCP...")
                                result = await session.call_tool(
                                    "get_weather", arguments={"cidade": cidade}
                                )
                                dados_brutos_clima = result.content[0].text
                                print(f"📊 [Dados MCP]: {dados_brutos_clima}")
                                
                                # ==========================================================
                                # PASSO 3: O CÉREBRO SINTETIZA (Formatando a Resposta)
                                # ==========================================================
                                print("🧠 [LLM] Formulando resposta final...")
                                prompt_final = f"""
                                O usuário perguntou: "{user_text}"
                                Os dados do sistema retornaram: {dados_brutos_clima}
                                Escreva uma resposta curta, amigável e direta para o usuário baseada estritamente nesses dados.
                                """
                                resposta_final = ai_client.models.generate_content(
                                    model=MODEL_ID, contents=prompt_final
                                )
                                final_answer = resposta_final.text
                                
                            else:
                                # Fluxo alternativo: O usuário apenas deu "Oi" ou não falou a cidade
                                resposta_generica = ai_client.models.generate_content(
                                    model=MODEL_ID,
                                    contents=f"O usuário disse: '{user_text}'. Responda de forma curta e amigável dizendo que você é um agente de clima e pergunte de qual cidade ele quer saber a previsão."
                                )
                                final_answer = resposta_generica.text
                            
                            # ==========================================================
                            # PASSO 4: DEVOLVE A RESPOSTA AO BARRAMENTO
                            # ==========================================================
                            await http_client.post(f"{BUS_URL}/send", json={
                                "sender": "meteorologista",
                                "target": msg["sender"],
                                "content": final_answer
                            })
                            print("✅ Resposta enviada ao AgentBus!")
                            
                    except Exception as e:
                        # Ignora falhas de conexão temporárias com o barramento
                        pass
                        
                    await asyncio.sleep(2)

if __name__ == "__main__":
    # A verificação de segurança agora garante que o .env funcionou
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERRO: Variável GEMINI_API_KEY não encontrada!")
        print("Verifique se você criou o arquivo .env na raiz do projeto com a sua chave.")
        exit(1)
        
    asyncio.run(main())