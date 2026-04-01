import asyncio
import aio_pika
import uuid
import logging
import json
import sys

# Configuração de Logging Centralizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [UI] %(levelname)s: %(message)s'
)
logger = logging.getLogger("interface")

# Identidade única e configurações
USER_ID = f"user_{str(uuid.uuid4())[:8]}"
RABBITMQ_URL = "amqp://guest:guest@localhost/"
EXCHANGE_NAME = "agents_exchange"
TARGET_AGENT = "meteorologista"

# Sincronizador de Prompt
response_received = asyncio.Event()
response_received.set()

async def main():
    logger.info(f"🚀 Iniciando Interface Real-time (ID: {USER_ID})")
    
    # 1. Lógica de Conexão Robusta
    connection = None
    retries = 5
    while retries > 0:
        try:
            logger.info(f"🔌 Tentando conectar ao RabbitMQ ({6-retries}/5)...")
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            break
        except Exception as e:
            retries -= 1
            logger.warning(f"⏳ Falha na conexão: {e}. Tentando novamente em 3s...")
            await asyncio.sleep(3)
    
    if not connection:
        logger.error("❌ Erro fatal: Não foi possível conectar ao RabbitMQ após 5 tentativas.")
        return

    async with connection:
        channel = await connection.channel()
        
        # 2. Configuração de Infraestrutura
        logger.info(f"📢 Declarando Exchange: {EXCHANGE_NAME}")
        exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC)
        
        logger.info(f"📥 Criando fila de resposta temporária: queue.{USER_ID}")
        queue = await channel.declare_queue(f"queue.{USER_ID}", auto_delete=True)
        await queue.bind(exchange, routing_key=USER_ID)
        
        logger.info("✅ Infraestrutura configurada com sucesso.")
        print(f"\n--- Chat Iniciado (ID: {USER_ID}) ---")
        print(f"Conversando com: {TARGET_AGENT}. Digite 'sair' para encerrar.\n")

        # 3. Callback de Resposta
        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    payload = json.loads(message.body.decode())
                    sender = payload.get('sender', 'Desconhecido')
                    content = payload.get('content', '')
                    
                    logger.info(f"📩 Resposta recebida de '{sender}'")
                    
                    # Limpeza visual do status "pensando..."
                    sys.stdout.write("\r" + " " * 70 + "\r")
                    sys.stdout.flush()

                    print(f"[🤖 {sender}]: {content}")
                    
                    # Libera o prompt
                    response_received.set()
                    
                except Exception as e:
                    logger.error(f"💥 Erro ao processar mensagem recebida: {e}", exc_info=True)
                    response_received.set()

        await queue.consume(on_message)

        # 4. Loop de Interação
        try:
            while True:
                # Aguarda a liberação do evento (trava o input se estiver esperando resposta)
                await response_received.wait()
                
                user_input = await asyncio.to_thread(input, f"[{USER_ID}] > ")
                
                if user_input.lower() in ["sair", "exit", "quit"]:
                    logger.info("👋 Usuário solicitou encerramento.")
                    break

                if not user_input.strip():
                    continue

                # Bloqueia o próximo input
                response_received.clear()

                payload = {
                    "sender": USER_ID,
                    "target": TARGET_AGENT,
                    "content": user_input
                }
                
                logger.info(f"📤 Enviando mensagem para '{TARGET_AGENT}'...")
                
                await exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(payload).encode(),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                    ),
                    routing_key=TARGET_AGENT
                )

                # Status visual
                sys.stdout.write(f"  ↳ 🧠 {TARGET_AGENT} está pensando...")
                sys.stdout.flush()

        except Exception as e:
            logger.error(f"🚨 Erro crítico no loop da interface: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Interface encerrada via teclado.")
    except Exception as e:
        logger.critical(f"💀 A aplicação colapsou: {e}")