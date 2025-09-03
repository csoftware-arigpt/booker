import os
import telebot
from telebot import types
import requests
from pyquery import PyQuery as pq
import tempfile

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

user_search_results = {}

def get_search_results(book_name, sort='sd2'):
    payload = {'ab': 'ab1', 't': book_name, 'sort': sort}
    r = requests.get('http://flibusta.is/makebooklist', params=payload)
    return r.text

def parse_search_results(html):
    doc = pq(html)
    books = []
    for div in doc.find('div'):
        book_element = pq(div)
        link = book_element('div > a')
        if link:
            title = link.text()
            href = link.attr('href')
            if href and href.startswith('/b/'):
                books.append({'title': title, 'href': href})
    return books

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me the name of a book and I will find it for you!")

@bot.message_handler(func=lambda message: True)
def handle_book_search(message):
    book_name = message.text
    html = get_search_results(book_name)
    if html == 'Не нашлось ни единой книги, удовлетворяющей вашим требованиям.':
        bot.reply_to(message, "Sorry, I couldn't find that book.")
        return
    books = parse_search_results(html)[:10]
    if not books:
        bot.reply_to(message, "No books found.")
        return
    user_search_results[message.chat.id] = books
    markup = types.InlineKeyboardMarkup()
    for idx, book in enumerate(books):
        btn_text = book['title']
        for pattern in ["(читать)", "(fb2)", "(epub)", "(mobi)", "(скачать epub)", "(скачать pdf)", "(скачать djvu)"]:
            btn_text = btn_text.replace(pattern, "")
        btn_text = btn_text.replace("  ", " - ").replace("  ", " ").replace("- -", "-")
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'book_{idx}'))
    bot.send_message(message.chat.id, "Choose a book:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('book_'))
def handle_book_selection(call):
    chat_id = call.message.chat.id
    book_index = int(call.data.split('_')[1])
    if chat_id not in user_search_results or book_index < 0 or book_index >= len(user_search_results[chat_id]):
        bot.send_message(chat_id, "Search results expired or invalid selection. Please search again.")
        return
    book = user_search_results[chat_id][book_index]
    book_url = f'http://flibusta.is{book["href"]}/epub'
    try:
        with requests.get(book_url, stream=True) as r:
            r.raise_for_status()
            book_id_link = book['href'].replace('/b', '').replace('/', '')
            temp_path = os.path.join(tempfile.gettempdir(), f"{book_id_link}.epub")
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        with open(temp_path, 'rb') as f:
            bot.send_document(chat_id, f)
        os.remove(temp_path)
    except Exception as e:
        bot.send_message(chat_id, f"Error downloading book: {str(e)}")

bot.polling()
