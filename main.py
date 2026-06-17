import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from pydantic import BaseModel

from bot import bot, dp
from storage import calculate_stats, save_event


class EventCreate(BaseModel):
    telegram_id: int
    stool_type: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Очищаем вебхуки перед запуском polling
    await bot.delete_webhook(drop_pending_updates=True)
    # Запускаем polling в фоновой задаче
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    # Корректное завершение при остановке сервера
    polling_task.cancel()
    await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.post("/events", status_code=201)
def create_event(event: EventCreate):
    save_event(event.telegram_id, event.stool_type)
    return {"status": "ok"}


@app.get("/stats")
def get_stats(telegram_id: int = Query(..., description="Telegram ID пользователя")):
    return calculate_stats(telegram_id)
