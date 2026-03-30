# mcp_server.py
import httpx
from mcp.server.fastmcp import FastMCP

# Inicializa o servidor
mcp = FastMCP("ServidorDeClimaReal")

@mcp.tool()
async def get_weather(cidade: str) -> str:
    """
    Consulta a previsão do tempo REAL e atualizada para uma cidade específica.
    Use esta ferramenta sempre que o usuário perguntar sobre o clima, temperatura ou se precisa de roupas específicas.
    """
    print(f"\n[MCP SERVER] 🌍 Buscando dados reais na internet para: {cidade}...")
    
    # Formatamos a cidade para a URL (substituindo espaços por '+')
    cidade_formatada = cidade.replace(" ", "+")
    url = f"https://wttr.in/{cidade_formatada}?format=j1"
    
    try:
        # Fazemos a chamada HTTP assíncrona para a API pública
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status() # Lança erro se a API cair
            
            dados = response.json()
            
            # Extraímos apenas as informações úteis do JSON gigante da API
            condicao_atual = dados['current_condition'][0]
            
            temperatura = condicao_atual['temp_C']
            sensacao = condicao_atual['FeelsLikeC']
            descricao = condicao_atual['lang_pt'][0]['value'] if 'lang_pt' in condicao_atual else condicao_atual['weatherDesc'][0]['value']
            umidade = condicao_atual['humidity']
            
            # Montamos um JSON limpo e mastigado para o nosso LLM entender facilmente
            resultado = {
                "cidade_buscada": cidade,
                "temperatura_celsius": temperatura,
                "sensacao_termica_celsius": sensacao,
                "condicao": descricao,
                "umidade_percentual": umidade
            }
            
            import json
            return json.dumps(resultado, ensure_ascii=False)
            
    except Exception as e:
        print(f"[MCP SERVER] ❌ Erro ao buscar clima: {e}")
        return f'{{"erro": "Não foi possível buscar o clima real para {cidade} no momento. Peça desculpas ao usuário."}}'

if __name__ == "__main__":
    # Roda nativamente via Stdio (sem abrir portas)
    mcp.run()