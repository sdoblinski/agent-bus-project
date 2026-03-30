# bus.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime
import uuid

# Inicializamos o app FastAPI
app = FastAPI(title="AgentBus", description="Barramento de mensagens leve para Sistemas Multi-Agentes")

# --- MODELOS DE DADOS (Pydantic) ---
class MessagePayload(BaseModel):
    """Payload recebido quando um agente quer enviar uma mensagem."""
    sender: str = Field(..., description="ID do agente que está enviando")
    target: str = Field(..., description="ID do agente de destino")
    content: str = Field(..., description="Conteúdo da mensagem ou tarefa")

class Message(BaseModel):
    """Estrutura interna da mensagem armazenada no barramento."""
    id: str
    sender: str
    target: str
    content: str
    timestamp: str

# --- ESTADO EM MEMÓRIA ---
# Dicionário onde a chave é o ID do agente (target) e o valor é uma lista de mensagens (fila)
# Exemplo: {"meteorologista": [Msg1, Msg2], "atendente": [Msg3]}
message_queues: Dict[str, List[Message]] = {}


# --- ENDPOINTS DA API ---

@app.post("/send", summary="Envia uma mensagem para o barramento")
async def send_message(payload: MessagePayload):
    """Recebe uma mensagem de um agente e a coloca na fila do agente de destino."""
    
    # Cria o objeto da mensagem com ID único e timestamp
    new_message = Message(
        id=str(uuid.uuid4()),
        sender=payload.sender,
        target=payload.target,
        content=payload.content,
        timestamp=datetime.now().isoformat()
    )
    
    # Se a fila do agente de destino não existir, criamos uma nova
    if payload.target not in message_queues:
        message_queues[payload.target] = []
        
    # Adicionamos a mensagem na fila correta
    message_queues[payload.target].append(new_message)
    
    print(f"[BUS] Nova mensagem: {payload.sender} -> {payload.target}")
    return {"status": "success", "message_id": new_message.id}


@app.get("/poll/{agent_id}", response_model=List[Message], summary="Lê e consome mensagens de um agente")
async def poll_messages(agent_id: str):
    """
    Agentes chamam este endpoint para ver se há mensagens para eles.
    Ao ler as mensagens, elas são removidas da fila (consumidas).
    """
    # Se não houver fila para o agente ou ela estiver vazia, retorna lista vazia
    if agent_id not in message_queues or not message_queues[agent_id]:
        return []
    
    # Pega todas as mensagens da fila
    messages_to_deliver = message_queues[agent_id]
    
    # Limpa a fila (já que as mensagens foram "entregues")
    message_queues[agent_id] = []
    
    if messages_to_deliver:
        print(f"[BUS] Entregando {len(messages_to_deliver)} mensagem(ns) para {agent_id}")
        
    return messages_to_deliver


# --- EXECUÇÃO ---
if __name__ == "__main__":
    # Roda o servidor na porta 8000
    print("Iniciando AgentBus na porta 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)