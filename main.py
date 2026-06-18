import asyncio
import logging

from bot import bot, dp


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    print("🤖 Робот 'Ритм ЖКТ' успешно запущен и слушает команды...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        print("\n🛑 Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
