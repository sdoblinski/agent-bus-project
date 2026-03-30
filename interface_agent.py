# interface_agent.py
import asyncio
import httpx
import sys

BUS_URL = "http://localhost:8000"
MY_ID = "atendente"
TARGET_ID = "meteorologista"

async def main():
    print("===================================================")
    print("🤖 Agente Atendente Iniciado!")
    print("Digite sua pergunta sobre o clima (ou 'sair' para fechar).")
    print("===================================================\n")
    
    async with httpx.AsyncClient() as client:
        while True:
            # 1. Captura o input do usuário humano
            user_input = input("👤 Você: ")
            
            if user_input.lower() in ['sair', 'exit', 'quit']:
                print("Encerrando o chat. Até logo!")
                break
                
            if not user_input.strip():
                continue

            # 2. Envia a pergunta para o Agente Meteorologista via AgentBus
            try:
                await client.post(f"{BUS_URL}/send", json={
                    "sender": MY_ID,
                    "target": TARGET_ID,
                    "content": user_input
                })
                print("⏳ [Enviado ao Barramento] Aguardando os agentes trabalharem...")
            except Exception as e:
                print(f"❌ Erro ao conectar no AgentBus: {e}")
                continue

            # 3. Faz "Polling" no barramento esperando a resposta voltar
            waiting_for_reply = True
            while waiting_for_reply:
                try:
                    # Pergunta ao AgentBus: "Tem mensagem para o 'atendente'?"
                    response = await client.get(f"{BUS_URL}/poll/{MY_ID}")
                    messages = response.json()
                    
                    if messages:
                        # Se chegou mensagem, imprime na tela e sai do loop de espera
                        for msg in messages:
                            print(f"\n🌤️ {msg['sender'].capitalize()}: {msg['content']}\n")
                        waiting_for_reply = False
                    else:
                        # Se não tem, dorme 1 segundo e pergunta de novo
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"❌ Erro ao ler o barramento: {e}")
                    await asyncio.sleep(2)

if __name__ == "__main__":
    # uv run python interface_agent.py
    asyncio.run(main())