import httpx
import json
import logging
import sys
from mcp.server.fastmcp import FastMCP

# Configura o logging para escrever APENAS no stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MCP] %(levelname)s: %(message)s',
    stream=sys.stderr  # <--- O segredo está aqui
)
logger = logging.getLogger("mcp_server")

mcp = FastMCP("ServidorDeClimaReal")

@mcp.tool()
async def get_weather(cidade: str) -> str:
    """
    Consulta a previsão do tempo REAL e atualizada para uma cidade específica.
    Use esta ferramenta sempre que o usuário perguntar sobre o clima ou temperatura.
    """
    # Substituímos o print por logger.info (vai para o stderr)
    logger.info(f"🌍 Buscando dados reais para: {cidade}...")
    
    cidade_formatada = cidade.replace(" ", "+")
    # Usamos o formato j1 para obter JSON da API wttr.in
    url = f"https://wttr.in/{cidade_formatada}?format=j1"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            
            dados = response.json()
            
            # Extração segura dos dados
            condicao_atual = dados['current_condition'][0]
            
            # Tenta pegar a descrição em português, senão cai para inglês
            descricao = condicao_atual.get('lang_pt', [{}])[0].get('value')
            if not descricao:
                descricao = condicao_atual.get('weatherDesc', [{}])[0].get('value', 'Não disponível')

            resultado = {
                "cidade_buscada": cidade,
                "temperatura_celsius": condicao_atual.get('temp_C'),
                "sensacao_termica_celsius": condicao_atual.get('FeelsLikeC'),
                "condicao": descricao,
                "umidade_percentual": condicao_atual.get('humidity')
            }
            
            logger.info(f"✅ Dados obtidos com sucesso para {cidade}.")
            return json.dumps(resultado, ensure_ascii=False)
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Erro HTTP na API wttr.in: {e}")
        return json.dumps({"erro": f"Cidade '{cidade}' não encontrada ou erro na API."})
    except Exception as e:
        logger.error(f"❌ Erro inesperado no MCP Server: {e}")
        return json.dumps({"erro": "Erro técnico ao processar clima. Peça desculpas."})

if __name__ == "__main__":
    # Rodar o servidor usando o transporte Stdio padrão
    logger.info("🚀 Servidor MCP de Clima iniciando transporte Stdio...")
    mcp.run()