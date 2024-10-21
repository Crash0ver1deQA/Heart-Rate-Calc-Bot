import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Константы для состояний
AGE, RESTING_HR = range(2)

# Словарь для временного хранения данных пользователей
user_data = {}

# Функция для расчета максимальной ЧСС и пульсовых зон с округлением до целого числа
def calculate_zones(age: int, resting_hr: int):
    max_hr = round(205.8 - (0.685 * age))  # Округляем до целого числа
    zone_1 = (round(resting_hr + (max_hr - resting_hr) * 0.5), round(resting_hr + (max_hr - resting_hr) * 0.6))  # 50-60%
    zone_2 = (round(resting_hr + (max_hr - resting_hr) * 0.6), round(resting_hr + (max_hr - resting_hr) * 0.7))  # 60-70%
    zone_3 = (round(resting_hr + (max_hr - resting_hr) * 0.7), round(resting_hr + (max_hr - resting_hr) * 0.8))  # 70-80%
    zone_4 = (round(resting_hr + (max_hr - resting_hr) * 0.8), round(resting_hr + (max_hr - resting_hr) * 0.9))  # 80-90%
    zone_5 = (round(resting_hr + (max_hr - resting_hr) * 0.9), max_hr)  # 90-100%
    return max_hr, zone_1, zone_2, zone_3, zone_4, zone_5

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Привет! Введите свой возраст:")
    return AGE  # Переходим к следующему состоянию

# Обработчик для получения возраста
async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    try:
        age = int(update.message.text.strip())
        if age < 1 or age > 150:
            await update.message.reply_text("Пожалуйста, введите возраст в пределах от 1 года до 150 лет:")
            return AGE

        user_data[user_id] = {'age': age}
        await update.message.reply_text("Отлично! Теперь введите свою ЧСС в покое:")
        return RESTING_HR  # Переходим к следующему состоянию
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный возраст:")
        return AGE  # Повторно запрашиваем возраст

# Обработчик для получения ЧСС в покое и расчета зон
async def get_resting_hr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    try:
        resting_hr = int(update.message.text.strip())
        if resting_hr < 20 or resting_hr > 100:
            await update.message.reply_text("Пожалуйста, введите ЧСС в покое в пределах от 20 до 100 уд./мин.:")
            return RESTING_HR

        user_data[user_id]['resting_hr'] = resting_hr

        # Получаем возраст из временных данных
        age = user_data[user_id]['age']

        # Рассчитываем максимальную ЧСС и зоны
        max_hr, zone_1, zone_2, zone_3, zone_4, zone_5 = calculate_zones(age, resting_hr)

        # Форматируем и отправляем ответ
        response = (f'Максимальная ЧСС: {max_hr} уд./мин.\n'
                    f'Пульсовая зона 1 (50-60%): {zone_1[0]} - {zone_1[1]} уд./мин.\n'
                    f'Пульсовая зона 2 (60-70%): {zone_2[0]} - {zone_2[1]} уд./мин.\n'
                    f'Пульсовая зона 3 (70-80%): {zone_3[0]} - {zone_3[1]} уд./мин.\n'
                    f'Пульсовая зона 4 (80-90%): {zone_4[0]} - {zone_4[1]} уд./мин.\n'
                    f'Пульсовая зона 5 (90-100%): {zone_5[0]} - {zone_5[1]} уд./мин.')
        await update.message.reply_text(response)

        # Добавляем кнопку "Начать заново" с использованием InlineKeyboardButton
        keyboard = [[InlineKeyboardButton("Начать заново", callback_data="restart")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Если хотите начать заново, нажмите на кнопку ниже:",
            reply_markup=reply_markup
        )

        # Очищаем данные после расчета
        del user_data[user_id]

        return ConversationHandler.END  # Завершаем диалог
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректную ЧСС в покое:")
        return RESTING_HR  # Повторно запрашиваем ЧСС

# Обработчик команды /cancel для отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отменено. Введите /start для начала заново.")
    return ConversationHandler.END

# Обработчик для нажатий на inline-кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    if query.data == "restart":
        # Убираем клавиатуру (inline-кнопки)
        await query.edit_message_reply_markup(reply_markup=None)
        # Отправляем команду /start пользователю для перезапуска диалога
        await query.message.reply_text("/start")

# Главная функция для запуска бота
async def main():
    # Токен бота
    application = ApplicationBuilder().token("TOKEN").build()

    # Определяем ConversationHandler для обработки состояний
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            RESTING_HR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_resting_hr)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))  # Здесь подключаем обработчик кнопок

    # Запуск бота
    await application.run_polling()

# Запуск бота с помощью текущего цикла событий
if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.run(main())