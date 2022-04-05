import logging
import random
import re

import redis

import telegram

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler
)

from environs import Env

from tg_log_handler import TelegramLogsHandler
from quiz_files_utils import make_questions_answers, multi_split

env = Env()
env.read_env()

logger = logging.getLogger(__file__)

CHOOSING = range(4)


def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    custom_keyboard = [['Новый вопрос', 'Сдаться'], ['Мой счёт', 'Выйти']]
    reply_markup = telegram.ReplyKeyboardMarkup(
        custom_keyboard, resize_keyboard=True)
    update.message.reply_text(text='Здравствуйте!', reply_markup=reply_markup)
    return CHOOSING


def handle_new_question_request(update: Update, context: CallbackContext) -> None:
    user = update.message.chat_id
    redis_session = context.bot_data['redis_session']
    question = random.choice(
        list(context.bot_data['questions_answers'].items()))[0]
    redis_session.set(user, question)
    reply_text = f'Новый вопрос: {question}'
    update.message.reply_text(text=reply_text)
    return CHOOSING


def handle_surrender(update: Update, context: CallbackContext) -> None:
    user = update.message.chat_id
    redis_session = context.bot_data['redis_session']
    question = redis_session.get(user)
    answer = multi_split(
        ['.', '('], context.bot_data['questions_answers'][question])[0]
    reply_text = (
        f'Вопрос: {question}\n'
        f'Правильный ответ: {answer}'
    )
    update.message.reply_text(text=reply_text)
    handle_new_question_request(update, context)


def handle_solution_attempt(update: Update, context: CallbackContext) -> None:
    user = update.message.chat_id
    reply_text = update.message.text
    redis_session = context.bot_data['redis_session']
    question = redis_session.get(user)
    answer = multi_split(
        ['.', '('], context.bot_data['questions_answers'][question])[0]
    if reply_text.upper().strip() == answer.upper().strip():
        reply_text = 'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»'
    else:
        reply_text = 'Неправильно… Попробуешь ещё раз?'
    update.message.reply_text(text=reply_text)
    return CHOOSING


def handle_score(update: Update, context: CallbackContext) -> None:
    user = update.message.chat_id
    update.message.reply_text(text='TODO Показать счёт...')


def cancel(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    update.message.reply_text(
        'Пока. Заходи ещё.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main():
    tg_token = env.str('TG_TOKEN')
    tg_token_admin = env.str('TG_TOKEN_ADMIN')
    tg_chat_id = env.str('TG_CHAT_ID')
    quiz_files_folder = env.str('QUIZ_FILES_FOLDER')
    redis_host = env.str('REDIS_HOST')
    redis_port = env.str('REDIS_PORT')
    redis_psw = env.str('REDIS_PSW')
    redis_session = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=0,
        password=redis_psw,
        decode_responses=True
    )

    tg_adm_bot = telegram.Bot(token=tg_token_admin)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.addHandler(TelegramLogsHandler(tg_adm_bot, tg_chat_id))
    logger.info('TG bot running...')

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.bot_data['redis_session'] = redis_session
    dispatcher.bot_data['questions_answers'] = make_questions_answers(
        quiz_files_folder)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [
                MessageHandler(Filters.regex('^Новый вопрос$'),
                               handle_new_question_request),
                MessageHandler(Filters.regex('^Сдаться$'), handle_surrender),
                MessageHandler(Filters.regex('^Мой счёт$'), handle_score),
                MessageHandler(Filters.regex('^Выйти$'), cancel),
                MessageHandler(Filters.text & ~Filters.command,
                               handle_solution_attempt)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
