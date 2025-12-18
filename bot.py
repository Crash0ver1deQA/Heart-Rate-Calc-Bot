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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

AGE, RESTING_HR = range(2)

# Функция расчёта (оставлена как в оригинале)
def calculate_zones(age: int, resting_hr: int):
    max_hr = round(205.8 - (0.685 * age))
    zone_1 = (round(resting_hr + (max_hr - resting_hr) * 0.5), round(resting_hr + (max_hr - resting_hr) * 0.6 - 1))
    zone_2 = (round(resting_hr + (max_hr - resting_hr) * 0.6), round(resting_hr + (max_hr - resting_hr) * 0.7 - 1))
    zone_3 = (round(resting_hr + (max_hr - resting_hr) * 0.7), round(resting_hr + (max_hr - resting_hr) * 0.8 - 1))
    zone_4 = (round(resting_hr + (max_hr - resting_hr) * 0.8), round(resting_hr + (max_hr - resting_hr) * 0.9 - 1))
    zone_5 = (round(resting_hr + (max_hr - resting_hr) * 0.9), max_hr)
    return max_hr, zone_1, zone_2, zone_3, zone_4, zone_5


# Универсальная функция start — работает и от /start, и от кнопки
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("👋 Привет! Введите свой возраст:")
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text="Расчёт перезапущен! 🔄", reply_markup=None)
        await query.message.reply_text("👋 Привет! Введите свой возраст:")
    return AGE


# Получение возраста
async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        if age < 1 or age > 150:
            await update.message.reply_text("❗ Пожалуйста, введите возраст в пределах от 1 года до 150 лет:")
            return AGE

        context.user_data["age"] = age
        await update.message.reply_text("👍 Отлично! Теперь введите свою ЧСС в покое:")
        return RESTING_HR
    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите корректный возраст:")
        return AGE


# Получение ЧСС и вывод результата (текст как в оригинале)
async def get_resting_hr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        resting_hr = int(update.message.text.strip())
        if resting_hr < 20 or resting_hr > 100:
            await update.message.reply_text("Пожалуйста, введите ЧСС в покое в пределах от 20 до 100 уд./мин.:")
            return RESTING_HR

        age = context.user_data["age"]
        max_hr, zone_1, zone_2, zone_3, zone_4, zone_5 = calculate_zones(age, resting_hr)

        response = (
            f'❤️ Максимальная ЧСС: {max_hr} уд./мин.\n'
            f'🟢 Пульсовая зона 1 (50-60%): {zone_1[0]} - {zone_1[1]} уд./мин. (восстановление / лёгкая активность)\n'
            f'🔵 Пульсовая зона 2 (60-70%): {zone_2[0]} - {zone_2[1]} уд./мин. (жиросжигание)\n'
            f'🟡 Пульсовая зона 3 (70-80%): {zone_3[0]} - {zone_3[1]} уд./мин. (аэробная выносливость)\n'
            f'🟠 Пульсовая зона 4 (80-90%): {zone_4[0]} - {zone_4[1]} уд./мин. (анаэробный порог)\n'
            f'🔴 Пульсовая зона 5 (90-100%): {zone_5[0]} - {zone_5[1]} уд./мин. (максимальная нагрузка)'
        )
        await update.message.reply_text(response)

        # Кнопка "Начать заново"
        keyboard = [[InlineKeyboardButton("Начать заново 🔄", callback_data="restart")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔄 Если хотите начать заново, нажмите на кнопку ниже:",
            reply_markup=reply_markup
        )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❗ Пожалуйста, введите корректную ЧСС в покое:")
        return RESTING_HR


# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отменено. Введите /start для начала заново.")
    context.user_data.clear()
    return ConversationHandler.END


def main():
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start, pattern="^restart$"),  # Перезапуск по кнопке
        ],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            RESTING_HR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_resting_hr)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)

    print("Бот запущен...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()