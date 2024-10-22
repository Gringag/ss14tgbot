import asyncio
import logging
import aiohttp
from urllib.parse import urlparse, urlunparse
from typing import Dict, Any
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

log = logging.getLogger("gamestatus")

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Список пользователей с доступом (по ID)
ACCESS_LIST = [7298108378, 1001266420]  # Замените на актуальные ID пользователей

async def get_server_status(addr: str) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(addr + "/status") as resp:
            resp.raise_for_status()  # Проверка на ошибки ответа
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
    user_id = update.message.from_user.id

    if user_id not in ACCESS_LIST:  # Проверка наличия доступа
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return
    
    if not addr:
        await update.message.reply_text("Укажите адрес сервера.")
        return

    message = await update.message.reply_text("Получение статуса сервера...")

    previous_text = ""
    
    try:
        while True:
            server_url = get_ss14_status_url(addr)
            json_data = await get_server_status(server_url)

            players_count = json_data.get("players", "?")
            max_players = json_data.get("soft_max_players", "?")
            round_id = json_data.get("round_id", "?")
            gamemap = json_data.get("map", "?")
            preset = json_data.get("preset", "?")

            rlevel = json_data.get("run_level", -1)
            status = "Unknown"
            if rlevel == 0:
                status = "Pre game lobby"
            elif rlevel == 1:
                status = "In game"
            elif rlevel == 2:
                status = "Post game"

            response_text = (
                f"🚀 Статус сервера: {status}\n"
                f"👥 Кол-во игроков: {players_count}/{max_players}\n"
                f"💡 ID раунда: {round_id}\n"
                f"🗺 Карта: {gamemap}\n"
                f"📦 Пресет: {preset}"
            )

            if response_text != previous_text:
                await message.edit_text(response_text, parse_mode="Markdown")
                previous_text = response_text

            await asyncio.sleep(10)  # Обновлять каждые 60 секунд

    except asyncio.CancelledError:
        log.info("Обновление статуса завершено.")
    except aiohttp.ClientError as e:
        log.exception("Ошибка сети: %s", str(e))
        await message.edit_text("Ошибка при подключении к серверу.", parse_mode="Markdown")
    except Exception as e:
        log.exception("Неизвестная ошибка: %s", str(e))
        await message.edit_text("Произошла ошибка.", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Используйте /status <адрес> чтобы проверять статус сервера.")

def main() -> None:
    application = ApplicationBuilder().token('token').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", update_status))

    try:
        application.run_polling()
    finally:
        log.info("Бот остановлен.")

if __name__ == '__main__':
    main()
