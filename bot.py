import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatType
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.dispatcher.event.bases import ErrorEvent

from config import (
    BOT_TOKEN,
    CHAT_ID,
    UPDATE_INTERVAL,
    get_topic_id,
    set_topic_id,
    CPU_CRIT,
    RAM_CRIT,
    DISK_CRIT,
    CRIT_CONFIRM_CYCLES,
)
from monitor import build_status_block, get_server_status, get_docker_stats

# ---------- ЛОГИ ----------

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ---------- ROUTER ----------

router = Router()
router.message.filter(F.chat.type != ChatType.PRIVATE)


@router.error()
async def global_error_handler(event: ErrorEvent):
    logging.critical(
        "Unhandled error: %r", event.exception, exc_info=True
    )


@router.message(Command("bind_here"))
async def bind_here(message: Message):
    thread_id = message.message_thread_id
    if thread_id is None:
        await message.answer(
            "Темы в этом чате не включены или команда вызвана не в теме."
        )
        return

    set_topic_id(thread_id)
    await message.answer(
        f"Ок, буду отправлять статусы в эту тему (id={thread_id})."
    )


@router.message(Command("status"))
async def send_status_once(message: Message):
    topic_id = message.message_thread_id or get_topic_id()

    block = build_status_block()
    text = f"<pre>\n{block}\n</pre>"

    await message.bot.send_message(
        chat_id=message.chat.id,
        text=text,
        parse_mode=ParseMode.HTML,
        message_thread_id=topic_id,
    )


async def periodic_status(bot: Bot):
    cpu_high_count = 0
    ram_high_count = 0
    disk_high_count = 0
    docker_was_ok = True

    while True:
        topic_id = get_topic_id()
        if topic_id is not None:
            # обычный статус
            block = build_status_block()
            text = f"<pre>\n{block}\n</pre>"
            try:
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    message_thread_id=topic_id,
                )
            except Exception as e:
                logging.exception(f"Ошибка при отправке статуса: {e}")

            # «сырые» значения для критики
            s = get_server_status()
            d = get_docker_stats()

            # Docker
            if d.get("ok"):
                if not docker_was_ok:
                    try:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text="✅ Docker снова доступен.",
                            message_thread_id=topic_id,
                        )
                    except Exception:
                        logging.exception(
                            "Ошибка при отправке уведомления о восстановлении Docker"
                        )
                docker_was_ok = True
            else:
                if docker_was_ok:
                    try:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"❌ Docker недоступен: {d.get('error', 'unknown')}",
                            message_thread_id=topic_id,
                        )
                    except Exception:
                        logging.exception(
                            "Ошибка при отправке уведомления о падении Docker"
                        )
                docker_was_ok = False

            # CPU/RAM/DISK
            if s.get("ok"):
                cpu = s["cpu"]
                ram = s["ram_percent"]
                disk = s["disk_percent"]

                cpu_high_count = cpu_high_count + 1 if cpu >= CPU_CRIT else 0
                ram_high_count = ram_high_count + 1 if ram >= RAM_CRIT else 0
                disk_high_count = disk_high_count + 1 if disk >= DISK_CRIT else 0

                alerts = []
                if cpu_high_count == CRIT_CONFIRM_CYCLES:
                    alerts.append(f"⚠️ CPU {cpu:.1f}% (>{CPU_CRIT}%)")
                if ram_high_count == CRIT_CONFIRM_CYCLES:
                    alerts.append(f"⚠️ RAM {ram:.1f}% (>{RAM_CRIT}%)")
                if disk_high_count == CRIT_CONFIRM_CYCLES:
                    alerts.append(f"⚠️ HDD {disk:.1f}% (>{DISK_CRIT}%)")

                if alerts:
                    try:
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text="Критическое состояние сервера:\n" + "\n".join(alerts),
                            message_thread_id=topic_id,
                        )
                    except Exception:
                        logging.exception(
                            "Ошибка при отправке критического уведомления"
                        )
            else:
                logging.warning(
                    f"Не удалось получить статус сервера: {s.get('error')}"
                )

        await asyncio.sleep(UPDATE_INTERVAL)


async def main():
    if not BOT_TOKEN or not CHAT_ID:
        logging.critical("BOT_TOKEN или CHAT_ID не заданы, проверь .env")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)

    logging.info(
        "Bot started. CHAT_ID=%s, UPDATE_INTERVAL=%s, topic_id=%s",
        CHAT_ID, UPDATE_INTERVAL, get_topic_id(),
    )

    asyncio.create_task(periodic_status(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
