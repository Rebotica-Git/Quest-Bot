import time
import telebot
from telebot import types
from loguru import logger
import db

bot = telebot.TeleBot("5436333781:AAFr8WefjBFdKvbYDne0nILhqWpbtQZq9rc")
logger.add("logs.log")
logger.success("Экземпляр бота создан")
m = types.Message

@bot.message_handler(['start'])
def start(msg: m):
    logger.info(f"Пользователь {msg.chat.id} нажал /start")
    old = db.db.s.get(db.Users, msg.chat.id)
    if not old:
        user = db.Users(id=msg.chat.id, name=msg.from_user.full_name, answers=None, is_admin=False)
        db.db.merge(user)
        db.db.commit()
    bot.send_message(msg.chat.id, "Пройти опрос — /lets_go")

@bot.message_handler(['lets_go'])
def quest(msg: m):
    data = db.db.s.get(db.Manage, 1)
    if data:
        logger.debug(f"Прочитали вопросы из manage: {data.questions}")
        data = ", ".join(data.questions)
        bot.send_message(msg.chat.id, "Вопросы: + " + data)
    else:
        logger.warning(f"Юзер {msg.chat.id} вызвал вопросы, но вопросов в таблице нет")
        bot.send_message(msg.chat.id, "Сейчас вопросов нет.")



@bot.message_handler(['write'])
def write(msg: m):
    data = db.Manage(id=1, short_name="Тестовые вопросы", questions=["Ты кто?", "Кто я?"])
    db.db.merge(data)
    data = db.Manage(id=2, short_name="Крутые вопросы", questions=["Ты крут?", "Докажи?"])
    db.db.merge(data)
    db.db.commit()
    logger.success(f"Админ {msg.chat.id} записал список вопросов с id={data.id}")


@bot.message_handler(['admin'])
def admin_check(msg: m):
    user = db.db.s.get(db.Users, msg.chat.id)
    if user.is_admin:
        logger.info(f"Админ {msg.chat.id} зашёл в меню администратора")
        admin_panel(msg)
    else:
        logger.warning(f"Юзер {msg.chat.id} стучится в меню администратора")
        start(msg)

def admin_panel(msg: m):
    keyboard = types.ReplyKeyboardMarkup(True)
    keyboard.row("Посмотреть списки вопросов", "Удалить список вопросов")
    keyboard.row("Добавить список вопросов")
    bot.send_message(msg.chat.id, "Выбери действие:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, admin_panel_handler)

def admin_panel_handler(msg: m):
    if msg.text.startswith("Посмотреть"):
        questions = check_questions()
        bot.send_message(msg.chat.id, questions_format(questions), parse_mode="HTML")
        time.sleep(3)
        admin_panel(msg)
    elif msg.text.startswith("Удалить"):
        delete_questions(msg)
    elif msg.text.startswith("Добавить"):
        pass
    else:
        admin_panel(msg)

@logger.catch
def check_questions():
    questions = []
    data = db.db.s.query(db.Manage)
    for d in data:
        questions.append([d.id, d.short_name, d.questions])
    logger.success("Раскудрявый, клён зелёный, лист резной")
    return questions

@logger.catch
def questions_format(questions: list):
    text = "Списки вопросов: \n\n"
    for q_list in questions:
        text += f"Список №{q_list[0]}\n"
        text += telebot.formatting.hbold(q_list[1]) + "\n"
        text += f"Вопросы: \n"
        for n, q in enumerate(q_list[2]):
            text += f"Вопрос №{n+1}. {q}\n"
        text += "\n"
    logger.info("Строка отформатирована успешно")
    return text

@logger.catch
def delete_questions(msg: m):
    questions = check_questions()
    ids = []
    keyboard = types.ReplyKeyboardMarkup(True, True)
    for q in questions:
        ids.append(q[0])
        keyboard.row(str(q[0]))

    text = "Выберите список для удаления: \n"
    for q in questions:
        text += telebot.formatting.hbold(f"Номер {q[0]}. {q[1]} \n")

    bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=keyboard)
    bot.register_next_step_handler(msg, delete_questions_handler, ids)

@logger.catch
def delete_questions_handler(msg: m, ids: list):
    if not msg.text.isnumeric():
        logger.warning(f"Админ {msg.chat.id} ввёл неверный номер списка")
        bot.send_message(msg.chat.id, "Введён неправильный номер списка")
        admin_panel(msg)
        return
    if int(msg.text) not in ids:
        logger.warning(f"Админ {msg.chat.id} ввёл неверный номер списка")
        bot.send_message(msg.chat.id, "Введён неправильный номер списка")
        admin_panel(msg)
        return

    keyboard = types.ReplyKeyboardMarkup(True, True)
    keyboard.row("я передумал")
    keyboard.row("УДАЛИТЬ")
    bot.send_message(msg.chat.id, f"Вы точно хотите удалить список №{msg.text}?", reply_markup=keyboard)
    bot.register_next_step_handler(msg, delete, int(msg.text))

@logger.catch
def delete(msg: m, num: int):
    if msg.text == "УДАЛИТЬ":
        db.db.s.query(db.Manage).filter(db.Manage.id == num).delete()
        db.db.commit()
        bot.send_message(msg.chat.id, f"Список №{num} успешно удалён!")
        logger.success(f"Список №{num} успешно удалён!")
    else:
        bot.send_message(msg.chat.id, "Удаление отменено.")
    admin_panel(msg)


bot.infinity_polling()
