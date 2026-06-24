import io
from contextlib import suppress
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import settings
from storage import (
    LOCAL_TZ,
    calculate_stats,
    clear_history,
    get_all_events,
    save_event,
)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()


def generate_progress_bar(current, total):
    if total == 0 or current == 0:
        return "░░░░░░░"

    percentage = int((current / total) * 7)
    filled = "🟩" * percentage
    empty = "░" * (7 - percentage)
    return f"{filled}{empty}"


def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💩 Отметить стул", callback_data="track")],
            [
                InlineKeyboardButton(
                    text="📊 Посмотреть статистику", callback_data="stats"
                )
            ],
        ]
    )


def stool_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💧 Жидкий", callback_data="type_1"),
                InlineKeyboardButton(text="☁️ Мягкий", callback_data="type_2"),
                InlineKeyboardButton(text="🧱 Твердый", callback_data="type_3"),
            ],
            [InlineKeyboardButton(text="ℹ️ Что выбрать?", callback_data="stool_help")],
            [InlineKeyboardButton(text="← Назад в меню", callback_data="main_menu")],
        ]
    )


def back_to_track_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Вернуться к выбору", callback_data="track")]
        ]
    )


def back_to_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Подробный отчет", callback_data="export_data"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Очистить историю", callback_data="confirm_clear"
                )
            ],
            [InlineKeyboardButton(text="← В главное меню", callback_data="main_menu")],
        ]
    )


def confirmation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💥 Да, удалить всё", callback_data="true_clear"
                ),
                InlineKeyboardButton(text="← Нет, отмена", callback_data="stats"),
            ]
        ]
    )


@dp.message(CommandStart())
async def start(message: types.Message):
    first_name = message.from_user.first_name
    await message.answer(
        f"👋 **Привет, {first_name}!**\n\n"
        f"Я твой личный трекер пищеварения. Помогу следить за "
        f"здоровьем кишечника и вовремя заметить отклонения. 🩺\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"🤖 Готов к работе 👇",
        reply_markup=main_keyboard(),
        parse_mode="Markdown",
    )


@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                text=("🤖 **Главное меню**\n\nВыбери необходимое действие ниже 👇"),
                reply_markup=main_keyboard(),
                parse_mode="Markdown",
            )


@dp.callback_query(lambda c: c.data == "track")
async def track(callback: types.CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                text=(
                    "💩 **Каким был твой стул в этот раз?**\n\nВыбери тип консистенции:"
                ),
                reply_markup=stool_keyboard(),
                parse_mode="Markdown",
            )


@dp.callback_query(lambda c: c.data == "stool_help")
async def stool_help(callback: types.CallbackQuery):
    await callback.answer()

    help_text = (
        "📖 **СПРАВОЧНИК КОНСИСТЕНЦИИ**\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        "☁️ **МЯГКИЙ (Близко к норме)**\n"
        "• **Форма:** Оформленная колбаска (гладкая или с трещинками), "
        "либо мягкий, слегка рыхлый стул. Допустима густая каша с границами.\n"
        "• **Статус:** В целом норма.\n\n"
        "💧 **ЖИДКИЙ**\n"
        "• **Форма:** Неоформленная кашица (как суп) или полностью "
        "водянистый стул.\n"
        "• **Статус:** Быстрое прохождение по кишечнику — вода не "
        "успела всосаться.\n\n"
        "🧱 **ТВЕРДЫЙ**\n"
        "• **Форма:** Отдельные жесткие комки (как орехи) или очень "
        "плотная, сухая колбаса.\n"
        "• **Статус:** Медленное прохождение — часто не хватает воды "
        "или клетчатки.\n\n"
        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        "💡 _Если стул напоминает густую кашу, но не растекается "
        "как вода — это ближе к мягкому варианту нормы._"
    )

    if isinstance(callback.message, Message):
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                text=help_text,
                reply_markup=back_to_track_keyboard(),
                parse_mode="Markdown",
            )


@dp.callback_query(lambda c: c.data.startswith("type_"))
async def save_event_handler(callback: types.CallbackQuery):
    parts = callback.data.split("_", 1)
    if len(parts) < 2 or not parts[1].isdigit():
        await callback.answer("❌ Данные повреждены", show_alert=True)
        return

    stool_type = int(parts[1])
    telegram_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name

    try:
        save_event(telegram_id, username, first_name, stool_type)
        await callback.answer()

        if isinstance(callback.message, Message):
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    text=("✨ **Запись сохранена**\n\n🤖 Жду следующую отметку 👇"),
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown",
                )
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        await callback.answer("🚨 Ошибка записи в базу данных", show_alert=True)
        if isinstance(callback.message, Message):
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    text=(
                        "❌ **Ошибка сохранения данных**\n"
                        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                        "Не удалось связаться с сервером. Попробуй позже."
                    ),
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown",
                )


@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id

    try:
        stats = calculate_stats(telegram_id)
        days_count = stats.get("days_count", 0)

        def render_pro_block(title, data_dict):
            total = data_dict.get("count", 0)
            types_data = data_dict.get("types", {1: 0, 2: 0, 3: 0})
            t1 = types_data.get(1, 0)
            t2 = types_data.get(2, 0)
            t3 = types_data.get(3, 0)

            return (
                f"{title} (Всего: `{total}`)\n"
                f"`💧 Жидкий  ` `{t1:<2}` {generate_progress_bar(t1, total)}\n"
                f"`☁️ Мягкий  ` `{t2:<2}` {generate_progress_bar(t2, total)}\n"
                f"`🧱 Твердый ` `{t3:<2}` {generate_progress_bar(t3, total)}"
            )

        if days_count == 0:
            days_text = "📅 **Ты еще не сделал ни одной отметки**"
        else:
            days_text = f"📅 **Сегодня {days_count}-й день отметок**"

        text = (
            f"📊 **АНАЛИТИКА ЗДОРОВЬЯ**\n"
            f"{days_text}\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
            f"{render_pro_block('☀️ **За сегодня**', stats['today'])}\n\n"
            f"{render_pro_block('📅 **За последние 7 дней**', stats['weekly'])}\n\n"
            f"{render_pro_block('📆 **За последние 30 дней**', stats['monthly'])}\n\n"
            f"{render_pro_block('📈 **За всё время**', stats['total'])}\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"🧬 *Индекс нормы: Идеальным считается преобладание мягкого "
            f"типа (☁️).*\n\n"
            f"💡 _Примечание: Твой персональный ритм ЖКТ и полноценная "
            f"медицинская картина сформируются после 30 дней регулярных отметок._"
        )

        if isinstance(callback.message, Message):
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    text=text,
                    reply_markup=back_to_menu_keyboard(),
                    parse_mode="Markdown",
                )
    except Exception as e:
        print(f"Ошибка аналитики: {e}")
        if isinstance(callback.message, Message):
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    text=(
                        "⚠️ **Не удалось загрузить отчет**\n"
                        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                        "Повтори запрос через пару секунд."
                    ),
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown",
                )


@dp.callback_query(lambda c: c.data == "confirm_clear")
async def confirm_clear(callback: types.CallbackQuery):
    await callback.answer()
    if isinstance(callback.message, Message):
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                text=(
                    "⚠️ **ВНИМАНИЕ!**\n"
                    "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                    "Ты действительно хочешь навсегда удалить всю историю записей?\n\n"
                    "🛑 *Это действие необратимо. Статистика обнулится.*"
                ),
                reply_markup=confirmation_keyboard(),
                parse_mode="Markdown",
            )


@dp.callback_query(lambda c: c.data == "true_clear")
async def true_clear(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        clear_history(telegram_id=telegram_id)
        await callback.answer()
        if isinstance(callback.message, Message):
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    text="🗑 История удалена",
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown",
                )
    except Exception as e:
        print(f"Ошибка при очистке БД: {e}")
        await callback.answer("🚨 Ошибка при удалении данных", show_alert=True)
        if isinstance(callback.message, Message):
            with suppress(TelegramBadRequest):
                await callback.message.edit_text(
                    text=(
                        "❌ **Не удалось очистить историю**\n"
                        "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
                        "Произошел системный сбой базы данных."
                    ),
                    reply_markup=main_keyboard(),
                    parse_mode="Markdown",
                )


@dp.callback_query(lambda c: c.data == "export_data")
async def export_data_handler(callback: types.CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id

    try:
        rows = get_all_events(telegram_id)

        if not rows:
            await callback.message.answer("У тебя пока нет записей для выгрузки 🤷‍♂️")
            return

        file_in_memory = io.StringIO()

        file_in_memory.write("📊 ПОДРОБНЫЙ ОТЧЕТ О СОСТОЯНИИ ЖКТ\n")

        gen_time = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
        file_in_memory.write(f"Сгенерирован: {gen_time} (Екатеринбург, UTC+5)\n")

        file_in_memory.write("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n")

        file_in_memory.write(f"{'Дата и время (Екб)':<22} | {'Тип стула'}\n")
        file_in_memory.write("-------------------------------------\n")

        stool_names = {1: "💧 Жидкий", 2: "☁️ Мягкий", 3: "🧱 Твердый"}

        for stool_type, created_at in rows:
            try:
                dt = datetime.fromisoformat(created_at)
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                formatted_date = created_at

            name = stool_names.get(stool_type, "Неизвестно")
            file_in_memory.write(f"{formatted_date:<22} | {name}\n")

        bytes_file = io.BytesIO(file_in_memory.getvalue().encode("utf-8-sig"))
        document = BufferedInputFile(bytes_file.read(), filename="my_gut_report.txt")

        await callback.message.answer_document(
            document, caption="Вот твой подробный отчет за всё время 📄"
        )

    except Exception as e:
        print(f"Ошибка формирования отчета: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при формировании файла. Попробуй позже."
        )
