import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from faq import find_best_answer, load_faq
from storage import SubscriberStorage


DEFAULT_SCORE_THRESHOLD = 65.0


def parse_admin_ids(raw: str | None) -> set[int]:
    if not raw:
        return set()
    return {int(value.strip()) for value in raw.split(",") if value.strip().isdigit()}


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан")

    admin_ids = parse_admin_ids(os.getenv("ADMIN_IDS"))
    faq_path = Path(os.getenv("FAQ_DOCX", "data/faq.docx"))
    subscribers_path = Path(os.getenv("SUBSCRIBERS_PATH", "data/subscribers.json"))

    bot = Bot(token=token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    storage = SubscriberStorage(subscribers_path)

    async def load_items() -> list:
        return load_faq(faq_path)

    @dp.message(CommandStart())
    async def handle_start(message: Message) -> None:
        await message.answer(
            "Привет! Я FAQ-бот. Просто напишите вопрос, и я постараюсь найти ответ.\n"
            "Команды: /help, /subscribe, /unsubscribe."
        )

    @dp.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(
            "Напишите вопрос в свободной форме.\n"
            "Чтобы получать уведомления о багфиксах, используйте /subscribe.\n"
            "Чтобы отписаться: /unsubscribe."
        )

    @dp.message(Command("subscribe"))
    async def handle_subscribe(message: Message) -> None:
        if storage.add(message.from_user.id):
            await message.answer("Вы подписаны на уведомления о багфиксах ✅")
        else:
            await message.answer("Вы уже подписаны на уведомления ✅")

    @dp.message(Command("unsubscribe"))
    async def handle_unsubscribe(message: Message) -> None:
        if storage.remove(message.from_user.id):
            await message.answer("Вы отписались от уведомлений.")
        else:
            await message.answer("Вы не были подписаны.")

    @dp.message(Command("bugfix"))
    async def handle_bugfix(message: Message) -> None:
        if message.from_user.id not in admin_ids:
            await message.answer("Команда доступна только администраторам.")
            return

        text = message.text or ""
        payload = text.replace("/bugfix", "", 1).strip()
        if not payload:
            await message.answer("Укажите текст уведомления: /bugfix <сообщение>")
            return

        subscribers = storage.list_all()
        if not subscribers:
            await message.answer("Нет подписчиков для рассылки.")
            return

        sent = 0
        for user_id in subscribers:
            try:
                await bot.send_message(user_id, f"🛠 <b>Багфикс:</b> {payload}")
                sent += 1
            except Exception as exc:  # noqa: BLE001 - логируем ошибки доставки
                logging.warning("Не удалось отправить уведомление %s: %s", user_id, exc)

        await message.answer(f"Уведомление отправлено {sent} подписчикам.")

    @dp.message(F.text)
    async def handle_question(message: Message) -> None:
        items = await load_items()
        item, score = find_best_answer(message.text, items)
        if item is None or score < DEFAULT_SCORE_THRESHOLD:
            await message.answer(
                "Не удалось найти точный ответ. Попробуйте переформулировать вопрос "
                "или уточнить детали."
            )
            return

        await message.answer(f"<b>Вопрос:</b> {item.question}\n\n{item.answer}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
