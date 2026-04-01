import asyncio
import aio_pika
import json
import logging
import os
import uuid
import chromadb
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from dotenv import load_dotenv

# Configurações iniciais
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [WORKER] %(levelname)s: %(message)s'
)
logger = logging.getLogger("worker")

load_dotenv()
RABBITMQ_URL = "amqp://guest:guest@localhost/"
EXCHANGE_NAME = "agents_exchange"
MODEL_ID = "gemini-3-flash-preview"

# Inicialização da IA e Memória
ai_client = genai.Client()
short_term_memory = {} 

print("💽 Conectando ao Banco Vetorial (ChromaDB)...")
db_client = chromadb.PersistentClient(path="./chroma_data")
memory_collection = db_client.get_or_create_collection(name="user_facts")

async def process_task(message: aio_pika.IncomingMessage, exchange, mcp_session):
    """
    Processa a tarefa com raciocínio completo: Memória + Ação + Síntese.
    """
    async with message.process(ignore_processed=True):
        try:
            body = message.body.decode()
            data = json.loads(body)
            user = data.get('sender', 'unknown')
            user_text = data.get('content', '')
            
            logger.info(f"📥 Processando: {user_text}")

            # 1. RECUPERAÇÃO DE CONTEXTO (RAG + Memória Curta)
            if user not in short_term_memory:
                short_term_memory[user] = []
            
            long_context = ""
            if memory_collection.count() > 0:
                search_results = memory_collection.query(query_texts=[user_text], n_results=3, where={"user": user})
                facts = search_results['documents'][0]
                if facts:
                    long_context = "Fatos: " + ", ".join(facts)
            
            history = "\n".join(short_term_memory[user][-4:])

            # --- ESTRATÉGIA: CHAMADA UNIFICADA (Poupa 1 chamada de cota) ---
            logger.info("🤖 Raciocinando (Cidade + Memória)...")
            brain_prompt = f"""
            Analise a conversa abaixo.
            Histórico: {history}
            Usuário disse: "{user_text}"
            
            Responda em formato JSON estrito:
            {{
                "city": "nome da cidade ou NENHUMA",
                "new_fact": "fato perene extraído ou VAZIO"
            }}
            """
            
            # Tenta a primeira chamada unificada
            brain_res = ai_client.models.generate_content(model=MODEL_ID, contents=brain_prompt)
            # Limpa possíveis markdown do JSON
            brain_data = json.loads(brain_res.text.replace('```json', '').replace('```', '').strip())
            
            city = brain_data.get("city", "NENHUMA")
            new_fact = brain_data.get("new_fact", "VAZIO")

            # 2. EXECUÇÃO DE AÇÃO (MCP)
            weather_data = "Sem dados de clima."
            if city != "NENHUMA":
                logger.info(f"🛠️ MCP: {city}")
                result = await mcp_session.call_tool("get_weather", arguments={"cidade": city})
                weather_data = result.content[0].text

            # 3. SÍNTESE FINAL (Segunda chamada)
            logger.info("✍️ Sintetizando...")
            synthesis_prompt = f"{long_context}\nClima: {weather_data}\nResponda ao usuário: {user_text}"
            final_answer_res = ai_client.models.generate_content(model=MODEL_ID, contents=synthesis_prompt)
            final_answer = final_answer_res.text

            # 4. SALVAMENTO (Memória)
            short_term_memory[user].extend([f"User: {user_text}", f"AI: {final_answer}"])
            if new_fact != "VAZIO":
                memory_collection.add(documents=[new_fact], metadatas=[{"user": user}], ids=[str(uuid.uuid4())])

            # 5. ENVIO
            await exchange.publish(
                aio_pika.Message(body=json.dumps({"sender": "meteorologista", "target": user, "content": final_answer}).encode()),
                routing_key=user
            )

        except Exception as e:
            if "429" in str(e):
                logger.warning("🚨 Cota do Gemini esgotada!")
                error_message = "Desculpe, meu cérebro atingiu o limite de processamento gratuito diário. Por favor, tente novamente em alguns minutos ou amanhã."
                await exchange.publish(
                    aio_pika.Message(body=json.dumps({"sender": "meteorologista", "target": user, "content": error_message}).encode()),
                    routing_key=user
                )
            else:
                logger.error(f"💥 Erro: {e}", exc_info=True)
                await message.reject(requeue=False)

async def main():
    # Conexão RabbitMQ
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC)

    # Conexão MCP
    server_params = StdioServerParameters(command="uv", args=["run", "python", "mcp_server.py"])
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()
            print("🧠 Worker Online (Contexto + Ação + Síntese)")
 
            queue = await channel.get_queue("tasks.meteorologista")
            async for message in queue:
                await process_task(message, exchange, mcp_session)

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERRO: GEMINI_API_KEY não encontrada.")
        exit(1)
    asyncio.run(main())