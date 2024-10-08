import asyncio
import logging
import aiohttp
from urllib.parse import urlparse, urlunparse
from typing import Dict, Any
from telegram import Update, Bot, Message
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

log = logging.getLogger("gamestatus")

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def get_server_status(addr: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(addr + "/status") as resp:
            return await resp.json()

def get_ss14_status_url(url: str) -> str:
    if "//" not in url:
        url = "//" + url

    parsed = urlparse(url, "ss14", allow_fragments=False)
    port = parsed.port or (443 if parsed.scheme == "ss14s" else 1212)
    scheme = "https" if parsed.scheme == "ss14s" else "http"

    return urlunparse((scheme, f"{parsed.hostname}:{port}", parsed.path, parsed.params, parsed.query, parsed.fragment))

async def update_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    addr = context.args[0] if context.args else None
    if not addr:
        await update.message.reply_text("Укажите адрес сервера.")
        return

    context.user_data["address"] = addr
    message = await update.message.reply_text("Получение статуса сервера...")
    
    while True:
        try:
            server_url = get_ss14_status_url(addr)
            json_data = await get_server_status(server_url)

            players_count = json_data.get("players", "?")
            max_players = json_data.get("soft_max_players", "?")
            round_id = json_data.get("round_id", "?")
            gamemap = json_data.get("map", "?")
            preset = json_data.get("preset", "?")

            rlevel = json_data.get("run_level")
            status = "Unknown"
            if rlevel == 0:
                status = "Pre game lobby"
            elif rlevel == 1:
                status = "In game"
            elif rlevel == 2:
                status = "Post game"

            response_text = (
                f"**Статус сервера:** {status}\n"
                f"**Игроков:** {players_count}/{max_players}\n"
                f"**ID раунда:** {round_id}\n"
                f"**Карта:** {gamemap}\n"
                f"**Preset:** {preset}"
            )

            await message.edit_text(response_text, parse_mode="Markdown")

            await asyncio.sleep(60)  # Обновлять каждые 60 секунд

        except Exception as e:
            log.exception("Failed to update server status: %s", str(e))
            await message.edit_text("Ошибка при обновлении статуса.", parse_mode="Markdown")
            break

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Используйте /status <адрес> чтобы проверять статус сервера.")

def main() -> None:
    application = ApplicationBuilder().token('7074181875:AAHlhY510AC9-fXZw3_Pd4SD-ko1oY1LR3o').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", update_status))

    application.run_polling()

if __name__ == '__main__':
    main()
