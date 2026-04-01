import asyncio
import json
import aio_pika
from contextlib import asynccontextmanager
from aio_pika.exceptions import QueueEmpty
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Configurações do RabbitMQ
RABBITMQ_URL = "amqp://guest:guest@localhost/"
EXCHANGE_NAME = "agents_exchange"
DLX_NAME = "agents_dlx"  # Dead Letter Exchange

class Message(BaseModel):
    sender: str
    target: str
    content: str

async def setup_rabbitmq():
    """
    Configura a infraestrutura inicial do RabbitMQ com lógica de retentativa.
    """
    retries = 5
    connection = None
    
    while retries > 0:
        try:
            # Tenta estabelecer a conexão robusta
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            channel = await connection.channel()

            # 1. Criar a Dead Letter Exchange e Fila (DLQ)
            dlx_exchange = await channel.declare_exchange(DLX_NAME, aio_pika.ExchangeType.TOPIC)
            dlq_queue = await channel.declare_queue("dead_letter_queue", durable=True)
            await dlq_queue.bind(dlx_exchange, routing_key="#")

            # 2. Criar a Exchange principal
            main_exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC)

            # 3. Criar a fila global para o Worker
            await channel.declare_queue(
                "tasks.meteorologist",
                durable=True,
                arguments={
                    "x-dead-letter-exchange": DLX_NAME,
                    "x-dead-letter-routing-key": "tasks.failed"
                }
            )
            
            # Vincula a fila do worker para ouvir mensagens do tipo 'meteorologist'
            worker_queue = await channel.get_queue("tasks.meteorologist")
            await worker_queue.bind(main_exchange, routing_key="meteorologist")

            print("✅ Conectado ao RabbitMQ e infraestrutura configurada!")
            return connection, main_exchange

        except Exception as e:
            retries -= 1
            print(f"⏳ Aguardando RabbitMQ ficar online... ({retries} tentativas restantes)")
            if retries == 0:
                print(f"❌ Erro fatal ao conectar no RabbitMQ: {e}")
                raise e
            await asyncio.sleep(3)

# Estado global para manter a conexão ativa
rabbit_connection = None
agents_exchange = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerenciador de ciclo de vida: Substitui o startup e shutdown.
    """
    global rabbit_connection, agents_exchange
    # Lógica de Inicialização (Startup)
    rabbit_connection, agents_exchange = await setup_rabbitmq()
    
    yield  # A aplicação roda aqui
    
    # Lógica de Encerramento (Shutdown)
    if rabbit_connection:
        await rabbit_connection.close()
        print("🛑 Conexão com RabbitMQ encerrada.")

app = FastAPI(lifespan=lifespan)

@app.post("/send")
async def send_message(msg: Message):
    """Envia a mensagem para a Exchange usando o target como routing_key."""
    try:
        await agents_exchange.publish(
            aio_pika.Message(
                body=msg.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=msg.target
        )
        return {"status": "sent", "routing_key": msg.target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/poll/{agent_id}")
async def poll_messages(agent_id: str):
    """Lógica de polling que consome do RabbitMQ tratando fila vazia."""
    async with rabbit_connection.channel() as channel:
        # Declara a fila
        queue = await channel.declare_queue(f"tasks.{agent_id}", auto_delete=True)
        await queue.bind(agents_exchange, routing_key=agent_id)

        messages = []
        try:
            while len(messages) < 10:
                try:
                    msg = await queue.get(no_ack=False, fail=True)
                    messages.append(json.loads(msg.body.decode()))
                    await msg.ack()
                except QueueEmpty:
                    break
        except Exception as e:
            print(f"❌ Erro ao processar fila: {e}")
            
        return messages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)