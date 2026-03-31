import asyncio
import httpx
import os
import uuid
import chromadb
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from dotenv import load_dotenv

load_dotenv()

BUS_URL = "http://localhost:8000"
MODEL_ID = "gemini-2.5-flash"
ai_client = genai.Client()

# Curto Prazo: Guarda as últimas conversas em RAM (reseta ao desligar)
short_term_memory = {} 

# Longo Prazo: Banco Vetorial persistente (salva numa pasta local chamada "chroma_data")
print("💽 Inicializando Banco de Dados Vetorial (ChromaDB)...")
db_client = chromadb.PersistentClient(path="./chroma_data")
memory_collection = db_client.get_or_create_collection(name="user_facts")

async def main():
    print("🌤️ Iniciando Agente Meteorologista com Memória...")
    
    server_params = StdioServerParameters(command="uv", args=["run", "python", "mcp_server.py"])
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[MCP] Conectado às ferramentas com sucesso!")
            
            async with httpx.AsyncClient() as http_client:
                print("[BUS] Aguardando tarefas no barramento...")
                while True:
                    try:
                        response = await http_client.get(f"{BUS_URL}/poll/meteorologista")
                        messages = response.json()
                        
                        for msg in messages:
                            user = msg['sender']
                            user_text = msg['content']
                            print(f"\n📩 [Nova Mensagem de {user}]: {user_text}")
                            
                            # Inicializa o histórico do usuário se for a primeira vez
                            if user not in short_term_memory:
                                short_term_memory[user] = []
                            
                            contexto_longo_prazo = ""
                            qtd_memorias = memory_collection.count()
                            if qtd_memorias > 0:
                                n_res = min(3, qtd_memorias) # Busca os 3 fatos mais relevantes
                                busca = memory_collection.query(query_texts=[user_text], n_results=n_res)
                                fatos = busca['documents'][0]
                                if fatos:
                                    contexto_longo_prazo = "\nFatos conhecidos sobre o usuário:\n- " + "\n- ".join(fatos)
                                    print("🧠 [Memória Recuperada]:", fatos)
                            
                            historico_curto = "\n".join(short_term_memory[user][-4:]) # Pega as últimas 4 falas
                            
                            # PASSO 1: Extrair a cidade considerando o histórico
                            prompt_extracao = f"""
                            Você é um assistente de clima.
                            Histórico recente da conversa:
                            {historico_curto}
                            
                            O usuário disse agora: "{user_text}"
                            Baseado na fala atual e no histórico, identifique a cidade que ele quer saber o clima.
                            Responda APENAS o nome da cidade. Se não for possível deduzir, responda 'NENHUMA'.
                            """
                            cidade = ai_client.models.generate_content(model=MODEL_ID, contents=prompt_extracao).text.strip()
                            
                            if cidade != "NENHUMA":
                                print(f"🛠️ [Ação] Consultando MCP para: {cidade}...")
                                result = await session.call_tool("get_weather", arguments={"cidade": cidade})
                                dados_clima = result.content[0].text
                                
                                # PASSO 2: Resposta final usando memórias
                                prompt_final = f"""
                                Você é um agente meteorologista empático.
                                {contexto_longo_prazo}
                                Histórico recente: {historico_curto}
                                
                                Dados do sistema: {dados_clima}
                                Pergunta atual do usuário: "{user_text}"
                                
                                Responda de forma natural, usando os dados e levando em conta as preferências do usuário, se houver.
                                """
                                final_answer = ai_client.models.generate_content(model=MODEL_ID, contents=prompt_final).text
                            else:
                                prompt_generico = f"Responda amigavelmente ao usuário: '{user_text}'. {contexto_longo_prazo}. Peça a cidade."
                                final_answer = ai_client.models.generate_content(model=MODEL_ID, contents=prompt_generico).text
                            
                            # Salva no Curto Prazo
                            short_term_memory[user].append(f"Usuário: {user_text}")
                            short_term_memory[user].append(f"Agente: {final_answer}")
                            
                            # Extrai fatos para o Longo Prazo (Vetorização)
                            prompt_fatos = f"""Analise a frase: "{user_text}". 
                            Extraia apenas fatos perenes ou preferências do usuário (ex: 'odeia frio', 'mora em São Paulo', 'chama-se Lucas').
                            Se não houver nenhum fato pessoal, responda apenas 'VAZIO'."""
                            
                            novo_fato = ai_client.models.generate_content(model=MODEL_ID, contents=prompt_fatos).text.strip()
                            if novo_fato != "VAZIO":
                                print(f"💾 [Salvando Fato Permanente]: {novo_fato}")
                                memory_collection.add(
                                    documents=[novo_fato],
                                    metadatas=[{"user": user}],
                                    ids=[str(uuid.uuid4())]
                                )
                            
                            await http_client.post(f"{BUS_URL}/send", json={"sender": "meteorologista", "target": user, "content": final_answer})
                            
                    except Exception as e:
                        pass
                    await asyncio.sleep(2)

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERRO: Variável GEMINI_API_KEY não encontrada no .env!")
        exit(1)
    asyncio.run(main())