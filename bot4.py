import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
AGE, RESTING_HR = range(2)


# Функция расчёта максимальной ЧСС и пульсовых зон
def calculate_zones(age: int, resting_hr: int):
    max_hr = round(205.8 - (0.685 * age))  # Формула Танака
    reserve = max_hr - resting_hr

    zones = {
        "1": (round(resting_hr + reserve * 0.5), round(resting_hr + reserve * 0.6)),  # 50–60%
        "2": (round(resting_hr + reserve * 0.6), round(resting_hr + reserve * 0.7)),  # 60–70%
        "3": (round(resting_hr + reserve * 0.7), round(resting_hr + reserve * 0.8)),  # 70–80%
        "4": (round(resting_hr + reserve * 0.8), round(resting_hr + reserve * 0.9)),  # 80–90%
        "5": (round(resting_hr + reserve * 0.9), max_hr),                            # 90–100%
    }
    return max_hr, zones


# Команда /start и перезапуск по кнопке
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Определяем, откуда пришёл вызов: от сообщения или от callback
    if update.message:
        await update.message.reply_text("Привет! Я помогу рассчитать ваши пульсовые зоны.\n\nВведите свой возраст (в годах):")
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text="Расчёт перезапущен! 🔄", reply_markup=None)
        await query.message.reply_text("Введите свой возраст (в годах):")

    return AGE


# Получение возраста
async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        if not (1 <= age <= 150):
            await update.message.reply_text("Пожалуйста, введите реальный возраст от 1 до 150 лет:")
            return AGE

        context.user_data["age"] = age
        await update.message.reply_text("Отлично! Теперь введите вашу ЧСС в покое (утренний пульс в состоянии полного отдыха):")
        return RESTING_HR
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите возраст числом (например, 35):")
        return AGE


# Получение ЧСС в покое и вывод результата
async def get_resting_hr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        resting_hr = int(update.message.text.strip())
        if not (20 <= resting_hr <= 100):
            await update.message.reply_text("ЧСС в покое обычно от 20 до 100 уд./мин.\nПожалуйста, введите правдоподобное значение:")
            return RESTING_HR

        age = context.user_data["age"]
        max_hr, zones = calculate_zones(age, resting_hr)

        response = (
            f"Ваш расчёт пульсовых зон:\n\n"
            f"Максимальная ЧСС: <b>{max_hr}</b> уд./мин\n\n"
            f"Зона 1 (50–60%) — восстановление: <b>{zones['1'][0]} – {zones['1'][1]}</b>\n"
            f"Зона 2 (60–70%) — жиросжигание: <b>{zones['2'][0]} – {zones['2'][1]}</b>\n"
            f"Зона 3 (70–80%) — аэробная: <b>{zones['3'][0]} – {zones['3'][1]}</b>\n"
            f"Зона 4 (80–90%) — анаэробный порог: <b>{zones['4'][0]} – {zones['4'][1]}</b>\n"
            f"Зона 5 (90–100%) — максимум: <b>{zones['5'][0]} – {zones['5'][1]}</b>"
        )

        await update.message.reply_text(response, parse_mode="HTML")

        # Кнопка "Начать заново"
        keyboard = [[InlineKeyboardButton("Начать заново", callback_data="restart")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Хотите рассчитать заново для другого возраста/пульса?", reply_markup=reply_markup)

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Пожалуйста, введите ЧСС числом (например, 60):")
        return RESTING_HR


# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Диалог отменён. Чтобы начать заново, отправьте /start")
    context.user_data.clear()
    return ConversationHandler.END


# Основная функция
def main():
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start, pattern="^restart$"),  # Кнопка теперь — точка входа!
        ],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            RESTING_HR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_resting_hr)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,  # Важно для повторных входов
    )

    application.add_handler(conv_handler)

    print("Бот запущен...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()