import logging
from dataclasses import dataclass
from typing import Final

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


# По вашему запросу токен хранится прямо в файле.
# Вставьте токен от @BotFather между кавычками.
BOT_TOKEN: Final = "YOUR_BOT_TOKEN_HERE"

MIN_AGE: Final = 1
MAX_AGE: Final = 120
MIN_RESTING_HR: Final = 20
MAX_RESTING_HR: Final = 100

AGE, RESTING_HR = range(2)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HeartRateZone:
    title: str
    intensity: str
    lower: int
    upper: int
    description: str
    icon: str


ZONE_INFO: Final = (
    ("Зона 1", "50–60%", "Восстановление", "🟢"),
    ("Зона 2", "60–70%", "Лёгкая выносливость", "🔵"),
    ("Зона 3", "70–80%", "Аэробная работа", "🟡"),
    ("Зона 4", "80–90%", "Пороговая нагрузка", "🟠"),
    ("Зона 5", "90–100%", "Максимальная нагрузка", "🔴"),
)

WELCOME_TEXT: Final = (
    "👋 <b>Рассчитаем ваши пульсовые зоны</b>\n\n"
    "Понадобятся возраст и пульс в покое. Лучше измерять его утром, "
    "до кофе и физической нагрузки.\n\n"
    f"<b>Шаг 1 из 2</b> · Введите возраст ({MIN_AGE}–{MAX_AGE}):"
)


def calculate_zones(age: int, resting_hr: int) -> tuple[int, list[HeartRateZone]]:
    """Рассчитать максимальную ЧСС и тренировочные зоны по резерву пульса."""
    max_hr = round(205.8 - 0.685 * age)
    heart_rate_reserve = max_hr - resting_hr
    boundaries = [
        round(resting_hr + heart_rate_reserve * intensity)
        for intensity in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
    ]

    zones = [
        HeartRateZone(
            title=title,
            intensity=intensity,
            lower=boundaries[index],
            upper=(
                boundaries[index + 1] - 1
                if index < len(ZONE_INFO) - 1
                else boundaries[index + 1]
            ),
            description=description,
            icon=icon,
        )
        for index, (title, intensity, description, icon) in enumerate(ZONE_INFO)
    ]
    return max_hr, zones


def format_result(
    age: int,
    resting_hr: int,
    max_hr: int,
    zones: list[HeartRateZone],
) -> str:
    zone_lines = "\n\n".join(
        (
            f"{zone.icon} <b>{zone.title} · {zone.intensity}</b>\n"
            f"   <code>{zone.lower}–{zone.upper} уд./мин.</code> · {zone.description}"
        )
        for zone in zones
    )
    return (
        "🫀 <b>Ваши пульсовые зоны</b>\n\n"
        f"Возраст: <b>{age}</b> · Пульс в покое: <b>{resting_hr}</b>\n"
        f"Расчётная максимальная ЧСС: <b>{max_hr} уд./мин.</b>\n\n"
        f"{zone_lines}\n\n"
        "ℹ️ Расчёт выполнен по резерву пульса и носит ориентировочный характер. "
        "При заболеваниях сердца и перед интенсивными тренировками "
        "проконсультируйтесь с врачом."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать новый расчёт по команде или кнопке."""
    context.user_data.clear()

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(WELCOME_TEXT, parse_mode=ParseMode.HTML)
    elif update.effective_message:
        await update.effective_message.reply_text(
            WELCOME_TEXT,
            parse_mode=ParseMode.HTML,
        )

    return AGE


async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message or not message.text:
        return AGE

    try:
        age = int(message.text.strip())
    except ValueError:
        await message.reply_text(
            "⚠️ Введите возраст целым числом, например: <b>30</b>",
            parse_mode=ParseMode.HTML,
        )
        return AGE

    if not MIN_AGE <= age <= MAX_AGE:
        await message.reply_text(
            f"⚠️ Возраст должен быть от {MIN_AGE} до {MAX_AGE}. Попробуйте ещё раз:"
        )
        return AGE

    context.user_data["age"] = age
    await message.reply_text(
        "Отлично 👍\n\n"
        f"<b>Шаг 2 из 2</b> · Введите пульс в покое "
        f"({MIN_RESTING_HR}–{MAX_RESTING_HR} уд./мин.):",
        parse_mode=ParseMode.HTML,
    )
    return RESTING_HR


async def get_resting_hr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message or not message.text:
        return RESTING_HR

    try:
        resting_hr = int(message.text.strip())
    except ValueError:
        await message.reply_text(
            "⚠️ Введите пульс целым числом, например: <b>60</b>",
            parse_mode=ParseMode.HTML,
        )
        return RESTING_HR

    if not MIN_RESTING_HR <= resting_hr <= MAX_RESTING_HR:
        await message.reply_text(
            f"⚠️ Пульс в покое должен быть от {MIN_RESTING_HR} "
            f"до {MAX_RESTING_HR} уд./мин. Попробуйте ещё раз:"
        )
        return RESTING_HR

    age = context.user_data.get("age")
    if not isinstance(age, int):
        context.user_data.clear()
        await message.reply_text(
            "Сессия устарела — начнём заново.\n\n" + WELCOME_TEXT,
            parse_mode=ParseMode.HTML,
        )
        return AGE

    max_hr, zones = calculate_zones(age, resting_hr)
    if resting_hr >= max_hr:
        await message.reply_text(
            "⚠️ Пульс в покое должен быть ниже расчётной максимальной ЧСС "
            f"({max_hr} уд./мин.). Проверьте значение:"
        )
        return RESTING_HR

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Рассчитать заново", callback_data="restart")]]
    )
    await message.reply_text(
        format_result(age, resting_hr, max_hr, zones),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )

    context.user_data.clear()
    return ConversationHandler.END


async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Пришлите значение обычным текстовым сообщением."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            "Доступные команды:\n"
            "/start — новый расчёт\n"
            "/cancel — отменить текущий расчёт\n"
            "/help — показать эту подсказку"
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_text(
            "Расчёт отменён. Чтобы начать заново, отправьте /start."
        )
    return ConversationHandler.END


async def setup_commands(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Рассчитать пульсовые зоны"),
            BotCommand("cancel", "Отменить расчёт"),
            BotCommand("help", "Помощь"),
        ]
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    logger.error(
        "Ошибка при обработке обновления",
        exc_info=(type(error), error, error.__traceback__) if error else None,
    )

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Произошла непредвиденная ошибка. Попробуйте снова: /start"
            )
        except TelegramError:
            logger.warning("Не удалось отправить сообщение об ошибке пользователю")


def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("Укажите токен Telegram-бота в константе BOT_TOKEN.")

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(setup_commands)
        .build()
    )

    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start, pattern=r"^restart$"),
        ],
        states={
            AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_age),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, invalid_input),
            ],
            RESTING_HR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_resting_hr),
                MessageHandler(~filters.TEXT & ~filters.COMMAND, invalid_input),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("help", help_command),
        ],
        allow_reentry=True,
    )

    application.add_handler(conversation_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_error_handler(error_handler)

    logger.info("Бот запущен")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
