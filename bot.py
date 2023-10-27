import time
import telebot
from telebot import types
from loguru import logger
import db

logger.remove()
logger.add("log.log", level="DEBUG", compression='zip', rotation='1 hour', retention='1 week')
logger.add("warn.log", level="WARNING", delay=True, rotation='1 hour')


bot = telebot.TeleBot("5436333781:AAGlDfZfB0_YJRjs9qacDR79KqCmOIxzTkE")
# logger.add("logs.log")
logger.success("Экземпляр бота создан")
m = types.Message
temp = {}

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
    questions = check_questions()
    ids = []

    keyboard = types.ReplyKeyboardMarkup(True, True)
    for q in questions:
        ids.append(q[0])
        keyboard.row(str(q[0]))

    text = "Выберите опрос: \n"
    for q in questions:
        text += telebot.formatting.hbold(f"Номер {q[0]}. {q[1]} \n")
    bot.send_message(msg.chat.id, text, parse_mode="HTML", reply_markup=keyboard)
    bot.register_next_step_handler(msg, first_question, ids)

def first_question(msg: m, ids: list):
    if not msg.text.isnumeric():
        logger.warning(f"Юзер {msg.chat.id} ввёл неверный номер списка")
        bot.send_message(msg.chat.id, "Введён неправильный номер списка")
        start(msg)
        return
    if int(msg.text) not in ids:
        logger.warning(f"Юзер {msg.chat.id} ввёл неверный номер списка")
        bot.send_message(msg.chat.id, "Введён неправильный номер списка")
        start(msg)
        return

    global temp
    temp[msg.chat.id] = {
        'list': int(msg.text),
        'queue': 0,
        'answers': []
    }
    logger.info(f"Клиент {msg.chat.id} инициализировал переменную - {temp[msg.chat.id] }")

    questions = db.db.s.get(db.Manage, int(msg.text)).questions
    bot.send_message(msg.chat.id, questions[0])
    bot.register_next_step_handler(msg, next_question, questions)

@logger.catch
def next_question(msg: m, questions):
    global temp
    temp[msg.chat.id]['answers'].append(msg.text)
    logger.info(f"Юзер {msg.chat.id} ответил на вопрос №{temp[msg.chat.id]['queue']} "
                f"списка №{temp[msg.chat.id]['list']}")

    if temp[msg.chat.id]['queue'] == len(questions) - 1:
        bot.send_message(msg.chat.id, "Спасибо за ответы!")
        logger.success(f"Юзер {msg.chat.id} завершил опрос!")
        save_client(msg)
        return

    temp[msg.chat.id]['queue'] += 1

    question = questions[temp[msg.chat.id]['queue']]
    bot.send_message(msg.chat.id, question)
    bot.register_next_step_handler(msg, next_question, questions)

def save_client(msg: m):
    user = db.db.s.get(db.Users, msg.chat.id)
    if user.answers is None:
        answers = [temp[msg.chat.id]['answers']]
    else:
        answers = user.answers
        answers.append(temp[msg.chat.id]['answers'])
    db.db.s.query(db.Users).filter_by(id=msg.chat.id).update({"answers": answers})
    db.db.commit()


@bot.message_handler(['check'])
def write(msg: m):
    user = db.db.s.get(db.Users, msg.chat.id)
    logger.debug(user.answers)


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
        ask_question(msg)
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

@logger.catch
def ask_question(msg: m):
    global temp
    temp[msg.chat.id] = []
    bot.send_message(msg.chat.id, "Введи первый вопрос:")
    bot.register_next_step_handler(msg, ask_next_question)

@logger.catch
def ask_next_question(msg: m):
    global temp
    if msg.text != "всё!":
        temp[msg.chat.id].append(msg.text)
        bot.send_message(msg.chat.id, "Введи следующий вопрос:")
        bot.register_next_step_handler(msg, ask_next_question)
    else:
        logger.info(f"Админ {msg.chat.id} создал новый список")
        bot.send_message(msg.chat.id, "Введи короткое имя:")
        bot.register_next_step_handler(msg, add_new_list)

@logger.catch
def add_new_list(msg: m):
    questions = check_questions()
    ids = []
    for q in questions:
        ids.append(q[0])
    num = max(ids) + 1
    new = db.Manage(id=num, short_name=msg.text, questions=temp[msg.chat.id])
    db.db.merge(new)
    db.db.commit()
    logger.success(f"Админ {msg.chat.id} записал новый список №{num}")
    bot.send_message(msg.chat.id, "Список успешно записан")
    time.sleep(2)
    admin_panel(msg)


bot.infinity_polling()
