import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Функция для расчета максимальной частоты сердечных сокращений и пульсовых зон
def calculate_zones(age: int, resting_hr: int):
    max_hr = 205.8 - (0.685 * age)
    zone_1 = (resting_hr + (max_hr - resting_hr) * 0.5, resting_hr + (max_hr - resting_hr) * 0.6)  # 50-60%
    zone_2 = (resting_hr + (max_hr - resting_hr) * 0.6, resting_hr + (max_hr - resting_hr) * 0.7)  # 60-70%
    zone_3 = (resting_hr + (max_hr - resting_hr) * 0.7, resting_hr + (max_hr - resting_hr) * 0.8)  # 70-80%
    zone_4 = (resting_hr + (max_hr - resting_hr) * 0.8, resting_hr + (max_hr - resting_hr) * 0.9)  # 80-90%
    zone_5 = (resting_hr + (max_hr - resting_hr) * 0.9, max_hr)        # 90-100%
    return max_hr, zone_1, zone_2, zone_3, zone_4, zone_5

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Чтобы рассчитать ЧСС, введи свой возраст и частоту сердечных сокращений в покое в формате: "Возраст, ЧСС".')

# Обработчик текстовых сообщений
async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Получаем данные от пользователя
        data = update.message.text.split(',')
        age = int(data[0].strip())
        resting_hr = int(data[1].strip())

        # Рассчитываем зоны
        max_hr, zone_1, zone_2, zone_3, zone_4, zone_5 = calculate_zones(age, resting_hr)

        # Форматируем и отправляем ответ
        response = (f'Максимальная ЧСС: {max_hr:.2f} уд/мин\n'
                    f'Пульсовая зона 1 (50-60%): {zone_1[0]:.2f} - {zone_1[1]:.2f} уд/мин\n'
                    f'Пульсовая зона 2 (60-70%): {zone_2[0]:.2f} - {zone_2[1]:.2f} уд/мин\n'
                    f'Пульсовая зона 3 (70-80%): {zone_3[0]:.2f} - {zone_3[1]:.2f} уд/мин\n'
                    f'Пульсовая зона 4 (80-90%): {zone_4[0]:.2f} - {zone_4[1]:.2f} уд/мин\n'
                    f'Пульсовая зона 5 (90-100%): {zone_5[0]:.2f} - {zone_5[1]:.2f} уд/мин')

        await update.message.reply_text(response)
    except (IndexError, ValueError):
        await update.message.reply_text('Ошибка! Пожалуйста, введите данные в формате: "возраст, ЧСС".')

async def main():
    # Токен API
    application = ApplicationBuilder().token("7668414589:AAHuRPic4g-Dvy6mv1o1cmwHquICYA6rRLI").build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, calculate))

    # Запускаем бота
    await application.run_polling()

# Запуск бота с помощью уже существующего цикла событий
if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()  # Это позволяет повторно использовать текущий цикл событий
    import asyncio
    asyncio.run(main())
