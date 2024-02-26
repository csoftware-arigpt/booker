import os
import telebot
from telebot import types
import requests
from pyquery import PyQuery as pq

bot_token = os.getenv('API_KEY_BOT')
bot = telebot.TeleBot(bot_token)

RATING = {
    'файл не оценен': 0,
    'файл на 1': 1,
    'файл на 2': 2,
    'файл на 3': 3,
    'файл на 4': 4,
    'файл на 5': 5
}

def get_search_result(book_name, sort):
    payload = {'ab': 'ab1', 't': book_name, 'sort': sort}
    r = requests.get('http://flibusta.is/makebooklist', params=payload)
    return r.text

def fetch_book_id(search_result, sort):
    doc = pq(search_result)
    if sort == 'litres':
        book = [pq(i)('div > a').attr.href for i in doc.find('div') if '[litres]' in pq(i).text().lower()][0]
    elif sort == 'rating':
        books = [(pq(i)('div > a').attr.href, pq(i)('img').attr.title) for i in doc.find('div')]
        book = sorted(books, key=lambda book: RATING[book[1]], reverse=True)[0][0]
    else:
        book = doc('div > a').attr.href
    return book

def get_book_link(book_name, sort, file_format):
    search_result = get_search_result(book_name, sort)
    if search_result == 'Не нашлось ни единой книги, удовлетворяющей вашим требованиям.':
        return 'No result'
    else:
        book = fetch_book_id(search_result, sort)
        link = f'http://flibusta.is{book}/{file_format}'
        return link

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me the name of a book and I will find it for you!")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    book_name = message.text
    book_link = get_book_link(book_name, 'sd2', 'epub')
    if book_link == 'No result':
        bot.reply_to(message, "Sorry, I couldn't find that book.")
    else:
        response = requests.get(book_link, stream=True)
        if response.status_code == 200:
            with open('book.epub', 'wb') as f:
                f.write(response.raw.read())

        markup = types.InlineKeyboardMarkup()
        download_button = types.InlineKeyboardButton("Download", callback_data="download")
        markup.add(download_button)
        bot.send_message(message.chat.id, "Here is your book", reply_markup=markup)
        
@bot.callback_query_handler(func=lambda call: call.data == "download")
def send_book(call):
    with open('book.epub', 'rb') as book_file:
        bot.send_document(call.message.chat.id, book_file)
    os.remove(f'book.epub')

bot.polling()

