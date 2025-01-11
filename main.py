import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime  # Для работы с датой и временем

# Замените на ваш токен от BotFather
TELEGRAM_BOT_TOKEN = '7269963709:AAFdkvZgawkyJ3zR3Jgxo9DFRb1fxU1KyJ8'

# ID пользователя, которому разрешён доступ к боту
ALLOWED_USER_ID = 294261815  # Замените на ваш user_id

# Состояния для ConversationHandler
ADD_LOGIN, ADD_NAME, ADD_TOKEN = range(3)
DELETE_ACCOUNT = range(1)

# Функция для проверки доступа
async def check_access(update: Update, context: CallbackContext):
    if update.message.from_user.id != ALLOWED_USER_ID:
        await update.message.reply_text("🚫 У вас нет доступа к этому боту.")
        return False
    return True

# Функция для загрузки данных из файла config.txt
def load_config(filename):
    """
    Загружает данные из файла config.txt.
    Возвращает список кортежей в формате (логин, токен, имя).
    """
    accounts = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()  # Убираем лишние пробелы и символы перевода строки
            if line and not line.startswith('['):  # Пропускаем пустые строки и секции
                try:
                    # Разделяем строку на части
                    login, token_and_name = map(str.strip, line.split(':', 1))
                    token, name = map(str.strip, token_and_name.split(',', 1))
                    accounts.append((login, token, name))
                except ValueError:
                    print(f"Ошибка в строке: {line}. Пропускаем.")
    return accounts

# Функция для сохранения данных в файл config.txt
def save_config(filename, accounts):
    """
    Сохраняет данные в файл config.txt.
    """
    with open(filename, 'w', encoding='utf-8') as file:
        file.write("[Accounts]\n")
        for login, token, name in accounts:
            file.write(f"{login}: {token}, {name}\n")

# Функция для получения баланса
def get_balance(login, token, name):
    url = 'https://api.direct.yandex.ru/live/v4/json/'
    data = {
        "method": "AccountManagement",
        "param": {
            "Action": "Get",
            "Logins": [login],
        },
        "token": token
    }
    response = requests.post(url, json=data)
    response_json = response.json()['data']['Accounts'][0]
    return f'{name} ({response_json["Login"]})\nBalance: {response_json["Amount"]} rub.'

# Команда /start
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    print(f"User ID: {user_id}")  # Выводим user_id в консоль
    await update.message.reply_text(f"Ваш user_id: {user_id}")

    if not await check_access(update, context):
        return

    keyboard = [['Получить балансы'], ['Добавить аккаунт'], ['Удалить аккаунт']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я бот для проверки балансов. Выберите действие:",
        reply_markup=reply_markup
    )

# Обработка нажатия кнопки "Получить балансы"
async def get_balances(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return

    # Загружаем данные из файла config.txt
    accounts = load_config('config.txt')

    # Получаем текущую дату и время
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    # Формируем заголовок с датой и временем
    header = f"На {current_time} остаток на балансах:\n\n"

    balances = []
    for login, token, name in accounts:
        try:
            balance_info = get_balance(login, token, name)
            balances.append(balance_info)
        except Exception as e:
            balances.append(f"Ошибка при получении баланса для {login}: {str(e)}")

    # Добавляем заголовок к балансам
    result_message = header + "\n-------------------------\n".join(balances)

    # Отправляем сообщение
    await update.message.reply_text(result_message)

# Обработка нажатия кнопки "Добавить аккаунт"
async def add_account_start(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return

    await update.message.reply_text(
        "Введите логин нового аккаунта:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_LOGIN

# Шаг 1: Получение логина
async def add_account_login(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return ConversationHandler.END

    context.user_data['login'] = update.message.text
    await update.message.reply_text("Введите имя аккаунта:")
    return ADD_NAME

# Шаг 2: Получение имени
async def add_account_name(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return ConversationHandler.END

    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите токен:")
    return ADD_TOKEN

# Шаг 3: Получение токена и сохранение аккаунта
async def add_account_token(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return ConversationHandler.END

    context.user_data['token'] = update.message.text

    # Загружаем текущие аккаунты
    accounts = load_config('config.txt')

    # Добавляем новый аккаунт
    accounts.append((context.user_data['login'], context.user_data['token'], context.user_data['name']))

    # Сохраняем обновленный список аккаунтов
    save_config('config.txt', accounts)

    # Возвращаем клавиатуру с командами
    keyboard = [['Получить балансы'], ['Добавить аккаунт'], ['Удалить аккаунт']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Аккаунт успешно добавлен!", reply_markup=reply_markup)
    return ConversationHandler.END

# Обработка нажатия кнопки "Удалить аккаунт"
async def delete_account_start(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return

    await update.message.reply_text(
        "Введите логин аккаунта, который хотите удалить:",
        reply_markup=ReplyKeyboardRemove()
    )
    return DELETE_ACCOUNT

# Шаг 1: Удаление аккаунта
async def delete_account(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return ConversationHandler.END

    login_to_delete = update.message.text

    # Загружаем текущие аккаунты
    accounts = load_config('config.txt')

    # Ищем аккаунт для удаления
    found_accounts = [acc for acc in accounts if acc[0] == login_to_delete]

    if found_accounts:
        # Удаляем аккаунт
        accounts = [acc for acc in accounts if acc[0] != login_to_delete]
        save_config('config.txt', accounts)

        # Возвращаем клавиатуру с командами
        keyboard = [['Получить балансы'], ['Добавить аккаунт'], ['Удалить аккаунт']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"Аккаунт {login_to_delete} успешно удален!", reply_markup=reply_markup)
    else:
        # Возвращаем клавиатуру с командами
        keyboard = [['Получить балансы'], ['Добавить аккаунт'], ['Удалить аккаунт']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(f"Аккаунт с логином {login_to_delete} не найден.", reply_markup=reply_markup)

    return ConversationHandler.END

# Отмена действий
async def cancel(update: Update, context: CallbackContext):
    if not await check_access(update, context):
        return ConversationHandler.END

    keyboard = [['Получить балансы'], ['Добавить аккаунт'], ['Удалить аккаунт']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Действие отменено.", reply_markup=reply_markup)
    return ConversationHandler.END

# Основная функция
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))

    # Обработчик для получения балансов
    application.add_handler(MessageHandler(filters.Text("Получить балансы"), get_balances))

    # Обработчик для добавления аккаунта
    add_account_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("Добавить аккаунт"), add_account_start)],
        states={
            ADD_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_login)],
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_name)],
            ADD_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_account_token)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(add_account_handler)

    # Обработчик для удаления аккаунта
    delete_account_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("Удалить аккаунт"), delete_account_start)],
        states={
            DELETE_ACCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_account)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(delete_account_handler)

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()