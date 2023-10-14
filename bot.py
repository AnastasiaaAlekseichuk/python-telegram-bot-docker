import telebot
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timezone
from flask import Flask, request

token = '6168298171:AAEOYzaYFtlZFs2zPvmH3BR6AXb_V0UnZ1M'
url = 'http://anastasiaalekseychuk.pythonanywhere.com/'
bot=telebot.TeleBot(token)

#Определение URL-адресов ELMA и передача пользовательского токена
elma = 'https://qcsrdpypy7vi4.elma365.ru'
elma_url = 'https://qcsrdpypy7vi4.elma365.ru/zadachi'
elma_url_task = 'https://qcsrdpypy7vi4.elma365.ru/pub/v1/app/zadachi/zadachi'
elma_token = '61ffd6d4-72d6-4505-a0e0-a80df14dde2a'


app = Flask(__name__)
bot.remove_webhook()
bot.set_webhook(url=url)

@app.route('/', methods={'POST'})
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

task_params = {}

#Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = ("Создать задачу")
    markup.add(btn1)
    bot.send_message(message.chat.id, text="Привет, {0.first_name}! Я бот-помощник для создания задач в ELMA. Создадим задачу?".format(message.from_user), reply_markup=markup)

#Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def task_name(message):
    if(message.text == "Создать задачу"):
        bot.send_message(message.chat.id, 'Введите название задачи')
        bot.register_next_step_handler(message, task_date)

#Функция для получения названия задачи от пользователя и сохранения его в глобальной 
#переменной task_params. Затем отправляется сообщение с запросом об определении срока 
#выполнения задачи
def task_date(message):
    global task_params
    task_params['context'] = {'__name': message.text}
    bot.send_message(message.chat.id, 'Название задачи: '+task_params['context']['__name'])
    bot.send_message(message.chat.id, 'Определите срок выполнения задачи в формате ГГГГ-ММ-ДД')
    bot.register_next_step_handler(message, task_executor)


#Функция для получения даты создания и срока выполнения задачи и сохранения их в глобальной
#переменной task_params. Затем отправляется сообщение с запросом о назначении исполнителя 
#задачи и вызывается функция gen_markup(), чтобы сгенерировать клавиатуру с возможными исполнителями
def task_executor(message):
    data_sozdaniya = datetime.now(timezone.utc).astimezone().isoformat()
    date_str = message.text+'T12:00:00'
    sdelat_do = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").astimezone().isoformat()
    global task_params
    task_params['context']['data_sozdaniya'] = data_sozdaniya
    task_params['context']['sdelat_do'] = sdelat_do
    bot.send_message(message.chat.id, 'Срок выполнения задачи: '+message.text)
    bot.send_message(message.chat.id, 'Кому назначить задачу?', reply_markup=gen_markup())
    

#Функция для создания клавиатуры с возможными исполнителями задачи на основе данных из ELMA, полученных 
#через API. Запрос выполняется методом GET к URL-адресу ELMA, указывая пользовательский токен для 
#авторизации.
def gen_markup():
    response = requests.get(elma+'/pub/v1/user/list', headers={'Authorization': 'Bearer '+elma_token})
    if response.status_code != 200:
        bot.send_message(message.chat.id, 'Ошибка создания задачи')
        return
    
    result = response.json()
    userlist = result['result']['result']

    print(len(userlist))

        
    markup = InlineKeyboardMarkup()
    markup.row_width = len(userlist)
    for user in userlist:
        markup.add(InlineKeyboardButton(user['__name'], callback_data=user['__id']))
    
    return markup

#Обработчик обратного вызова (callback), вызываемого при нажатии кнопки с исполнителем задачи. Обработчик 
#получает данные о выбранном исполнителе, сохраняет их в параметрах задачи и вызывает функцию task_create() 
#для создания задачи
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    new_markup = types.InlineKeyboardMarkup()
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=new_markup)
    global task_params
    task_params['context']['ispolnitel'] = [call.data]
    
    bot.send_message(call.message.chat.id, "Назначить задачу пользователю "+call.data)
    task_create(call.message)



#Функция для создания задачи в ELMA на основе параметров task_params, отправляет POST-запрос к 
#URL-адресу ELMA с передачей параметров и пользовательского токена для авторизации. Затем происходит 
#проверка успешности создания задачи и отправляется сообщение пользователю о результате
def task_create(message):
    print(task_params)
    response = requests.post(elma_url_task+'/create', json=task_params, headers={'Authorization': 'Bearer '+elma_token})
    if response.status_code != 200:
        bot.send_message(message.chat.id, 'Ошибка создания задачи')
        return
    
    result = response.json()
    print(result)
    if result['success'] == False:
        bot.send_message(message.chat.id, 'Шо-то пошло не так')
    else:
        bot.send_message(message.chat.id, 'Задача создана успешно [Посмотреть задачу]('+elma_url+'(p:item/zadachi/zadachi/'+result['item']['__id']+'\))', parse_mode='MarkdownV2')
    print(result['success'])