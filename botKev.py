import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv  # Adicionado para carregar .env
import google.generativeai as genai
import asyncio

# --- Configuração Inicial de Logging ---
# Melhorar o formato para incluir o nome do módulo e linha, útil para depuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(lineno)d - %(message)s')
logger = logging.getLogger('discord_bot')

# --- Carregamento de Variáveis de Ambiente ---
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')  # Use getenv para segurança
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Use getenv para segurança
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID')) if os.getenv('BOT_OWNER_ID') else None

# --- Validação das Variáveis de Ambiente Essenciais ---
if not DISCORD_BOT_TOKEN:
    logger.error(
        "Erro FATAL: Variável de ambiente DISCORD_BOT_TOKEN não encontrada. Certifique-se de que seu arquivo .env está configurado.")
    exit(1)

if not GEMINI_API_KEY:
    logger.error(
        "Erro FATAL: Variável de ambiente GEMINI_API_KEY não encontrada. Certifique-se de que seu arquivo .env está configurado.")
    exit(1)

# --- Definição das Intents do Discord ---
# Recomenda-se Intents.default() e adicionar message_content explicitamente
intents = discord.Intents.default()
intents.message_content = True  # Necessário para ler o conteúdo das mensagens

# --- Inicialização do Bot (usando commands.Bot) ---
# commands.Bot é preferível para bots que usam comandos
bot = commands.Bot(command_prefix='!', intents=intents, owner_id=BOT_OWNER_ID)

# --- Configuração da API do Google Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ API do Google Gemini configurada com sucesso.")

    generation_config = {
        'candidate_count': 1,
        'temperature': 0.5,
        'max_output_tokens': 150,
    }

    # --- AQUI ESTÁ A MUDANÇA ESSENCIAL ---
    # Defina o NOME EXATO do modelo como uma string.
    # Ex: 'gemini-1.0-pro', 'gemini-1.0-pro-001', 'gemini-1.5-flash-latest', 'gemini-1.5-pro-latest'
    # Eu mantenho 'gemini-1.0-pro' como no seu último código, mas ajuste se precisar de outro.
    GEMINI_MODEL_NAME_TO_USE = 'gemini-2.0-flash' # <--- VERIFIQUE E ATUALIZE ESTA LINHA!

    # Carrega o modelo Gemini UMA VEZ usando o nome da string
    gemini_model = genai.GenerativeModel(model_name=GEMINI_MODEL_NAME_TO_USE,
                                         generation_config=generation_config)
    logger.info(f"✅ Modelo Gemini '{GEMINI_MODEL_NAME_TO_USE}' carregado.")
except Exception as e:
    # A linha 62 é o 'except', mas o problema acontece na linha de cima se 'model_name' não for string.
    logger.error(f"Erro FATAL: Falha ao configurar a API ou carregar o modelo Gemini. Detalhes: {e}")
    logger.error("Verifique se o nome do modelo está correto (é uma string como 'gemini-1.0-pro') e se sua API Key é válida.")
    exit(1)

# Dicionário para armazenar o histórico de chat por canal
# Isso permite que cada canal tenha sua própria conversa contínua com o Gemini.
chat_sessions = {}  # {channel_id: gemini_chat_object}


# --- Eventos do Bot ---
@bot.event
async def on_ready():
    logger.info(f"🥳 Bot {bot.user.name} está online e conectado!")
    logger.info(f"Estou em {len(bot.guilds)} servidor(es)!")
    try:
        # Sincroniza comandos de barra.
        # Se você tiver comandos de barra, eles serão registrados ou atualizados.
        synced = await bot.tree.sync()
        logger.info(f"✅ Sincronizei {len(synced)} comando(s) de barra globalmente.")
    except Exception as e:
        logger.exception(f"❌ Falha ao sincronizar comandos de barra globalmente: {e}")


@bot.event
async def on_message(message: discord.Message):
    # Ignora mensagens de outros bots ou do próprio bot
    if message.author.bot:
        return

    # Processa comandos de prefixo (se você tiver algum)
    await bot.process_commands(message)

    # Lógica para quando o bot é mencionado ou a mensagem é um DM
    # Se a mensagem for um DM ou o bot for explicitamente mencionado
    if isinstance(message.channel, discord.DMChannel) or bot.user in message.mentions:
        async with message.channel.typing():  # Mostra que o bot está "digitando"
            user_message_content = message.content

            # Remove a menção ao bot do conteúdo da mensagem
            if bot.user in message.mentions:
                user_message_content = user_message_content.replace(f"<@{bot.user.id}>", "").strip()

            # Se a mensagem ficou vazia após remover a menção, ignora
            if not user_message_content:
                await message.reply("Olá! Como posso ajudar?")
                return

            # Obtém ou cria uma sessão de chat para o canal
            if message.channel.id not in chat_sessions:
                chat_sessions[message.channel.id] = gemini_model.start_chat(history=[])
                logger.info(f"Iniciada nova sessão de chat Gemini para o canal {message.channel.id}.")

            current_chat = chat_sessions[message.channel.id]

            try:
                logger.info(f"Perguntando ao Gemini (canal {message.channel.id}): '{user_message_content}'")

                # Envia a mensagem do usuário para o chat Gemini
                # Usar asyncio.to_thread para chamadas síncronas da API Gemini para não bloquear o bot
                response = await asyncio.to_thread(current_chat.send_message, user_message_content)

                # Acessa o texto da resposta
                gemini_response_text = response.text.strip()
                logger.info(f"🤖 Resposta do Gemini (canal {message.channel.id}): '{gemini_response_text}'")

                await message.reply(gemini_response_text)

            except genai.types.BlockedPromptException as e:
                logger.warning(f"A pergunta foi bloqueada pelo Gemini: {e}")
                await message.reply(
                    "⚠️ Sua pergunta foi bloqueada devido a políticas de segurança ou conteúdo. Por favor, tente reformular.")
            except Exception as e:
                logger.exception(f"Erro inesperado ao processar pergunta com Gemini no canal {message.channel.id}: {e}")
                await message.reply(
                    f"❌ Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente. Detalhes: `{e}`")


# --- Comandos de Barra (Slash Commands) ---
# Se você quiser comandos de barra, você pode adicioná-los aqui,
# similar ao seu código anterior, dentro de uma Cog ou diretamente.
# Exemplo de comando de barra simples:
@bot.tree.command(name="reset_chat", description="Reseta a conversa com o Gemini neste canal.")
async def reset_chat(interaction: discord.Interaction):
    if interaction.channel_id in chat_sessions:
        del chat_sessions[interaction.channel_id]
        logger.info(f"Sessão de chat Gemini resetada para o canal {interaction.channel.id}.")
        await interaction.response.send_message("✅ Conversa com o Gemini resetada para este canal!", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ Nenhuma conversa ativa com o Gemini para resetar neste canal.",
                                                ephemeral=True)


# --- Execução Principal do Bot ---
if __name__ == "__main__":
    try:
        logger.info("Iniciando o loop de eventos do asyncio para o bot.")
        bot.run(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logger.error("Erro de login: Token do bot inválido. Verifique o DISCORD_BOT_TOKEN no seu arquivo .env.")
    except KeyboardInterrupt:
        logger.info("Bot desligado manualmente via KeyboardInterrupt.")
    except Exception as e:
        logger.exception(f"Erro fatal durante a execução do bot: {e}")