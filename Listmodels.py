import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Configuração de Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('model_lister')

# Carregar variáveis de ambiente
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    logger.error("Erro: Variável de ambiente GEMINI_API_KEY não encontrada. Certifique-se de que seu arquivo .env está configurado.")
    exit(1)

try:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("API do Google Gemini configurada.")

    print("\n--- Modelos Gemini disponíveis para 'generateContent' (chat/texto): ---")
    models_found = False
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            # Imprime o nome completo do modelo e o displayName para facilitar a identificação
            print(f"- Nome da API: {m.name.split('/')[-1]} (Nome Completo: {m.name}, Display Name: {m.display_name})")
            models_found = True

    if not models_found:
        print("Nenhum modelo compatível com 'generateContent' encontrado. Verifique sua chave de API ou as permissões.")

except Exception as e:
    logger.error(f"Erro ao tentar listar modelos: {e}")
    logger.error("Verifique se sua GEMINI_API_KEY está correta e ativa.")