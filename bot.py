from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from storage import calculate_stats, clear_history, save_event

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
        f"Я твой личный трекер пищеварения. Помогу следить за здоровьем кишечника и вовремя заметить отклонения. 🩺\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"🤖 Готов к работе 👇",
        reply_markup=main_keyboard(),
        parse_mode="Markdown",
    )


@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        f"🤖 Готов к работе 👇",
        reply_markup=main_keyboard(),
        parse_mode="Markdown",
    )


@dp.callback_query(lambda c: c.data == "track")
async def track(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        f"📝 **Фиксация состояния**\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\nВыбери консистенцию стула:",
        reply_markup=stool_keyboard(),
        parse_mode="Markdown",
    )


@dp.callback_query(lambda c: c.data == "stool_help")
async def stool_help(callback: types.CallbackQuery):
    await callback.answer()

    help_text = (
        f"📖 **СПРАВОЧНИК КОНСИСТЕНЦИИ**\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"☁️ **МЯГКИЙ (Близко к норме)**\n"
        f"• **Форма:** Оформленная колбаска (гладкая или с трещинками), либо мягкий, слегка рыхлый стул. Допустима густая каша с границами.\n"
        f"• **Статус:** В целом норма.\n\n"
        f"💧 **ЖИДКИЙ**\n"
        f"• **Форма:** Неоформленная кашица (как суп) или полностью водянистый стул.\n"
        f"• **Статус:** Быстрое прохождение по кишечнику — вода не успела всосаться.\n\n"
        f"🧱 **ТВЕРДЫЙ**\n"
        f"• **Форма:** Отдельные жесткие комки (как орехи) или очень плотная, сухая колбаса.\n"
        f"• **Статус:** Медленное прохождение — часто не хватает воды или клетчатки.\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"💡 _Если стул напоминает густую кашу, но не растекается как вода — это ближе к мягкому варианту нормы._"
    )

    await callback.message.edit_text(
        help_text, reply_markup=back_to_track_keyboard(), parse_mode="Markdown"
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
        save_event(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            stool_type=stool_type,
        )

        stool_names = {1: "Жидкий", 2: "Мягкий", 3: "Твердый"}
        current_name = stool_names.get(stool_type, "Новый")

        await callback.answer("")

        await callback.message.edit_text(
            f"✨ **Запись сохранена: {current_name}**\n\n🤖 Жду следующую отметку 👇",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        await callback.answer("🚨 Ошибка записи в базу данных", show_alert=True)
        await callback.message.edit_text(
            f"❌ **Ошибка сохранения данных**\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"Не удалось связаться с сервером. Пожалуйста, попробуйте позже.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )


@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    await callback.answer()
    telegram_id = callback.from_user.id

    try:
        stats = calculate_stats(telegram_id)

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

        text = (
            f"📊 **АНАЛИТИКА ЗДОРОВЬЯ**\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
            f"{render_pro_block('☀️ **За сегодня**', stats['today'])}\n\n"
            f"{render_pro_block('📅 **За последние 7 дней**', stats['weekly'])}\n\n"
            f"{render_pro_block('📆 **За последние 30 дней**', stats['monthly'])}\n\n"
            f"{render_pro_block('📈 **За всё время**', stats['total'])}\n\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"🧬 *Индекс нормы: Идеальным считается преобладание мягкого типа (☁️).*\n\n"
            f"💡 _Примечание: Твой персональный ритм ЖКТ и полноценная медицинская картина сформируются после 30 дней регулярных отметок._"
        )

        await callback.message.edit_text(
            text, reply_markup=back_to_menu_keyboard(), parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка аналитики: {e}")
        await callback.message.edit_text(
            f"⚠️ **Не удалось загрузить отчет**\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"Повтори запрос через пару секунд.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )


@dp.callback_query(lambda c: c.data == "confirm_clear")
async def confirm_clear(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        f"⚠️ **ВНИМАНИЕ!**\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"Ты действительно хочешь навсегда удалить всю историю записей?\n\n"
        f"🛑 *Это действие необратимо. Статистика обнулится.*",
        reply_markup=confirmation_keyboard(),
        parse_mode="Markdown",
    )


@dp.callback_query(lambda c: c.data == "true_clear")
async def true_clear(callback: types.CallbackQuery):
    telegram_id = callback.from_user.id
    try:
        clear_history(telegram_id=telegram_id)
        await callback.answer()
        await callback.message.edit_text(
            "🗑 История удалена",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Ошибка при очистке БД: {e}")
        await callback.answer("🚨 Ошибка при удалении данных", show_alert=True)
        await callback.message.edit_text(
            f"❌ **Не удалось очистить историю**\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"Произошел системный сбой базы данных.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )
