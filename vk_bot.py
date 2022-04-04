from email import message
import logging
import redis
import vk_api
import random

from environs import Env
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id

from quiz_files_utils import make_questions_answers, multi_split

env = Env()
env.read_env()

logger = logging.getLogger(__file__)


def make_keyboard():
    keyboard = VkKeyboard()
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('Мой счёт', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Выйти', color=VkKeyboardColor.NEGATIVE)
    return keyboard


def handle_solution_attempt(event, vk_bot, redis_session, questions_answers):
    user_id = event.user_id
    keyboard = make_keyboard()
    question = redis_session.get(user_id)
    if not question:
        vk_bot.messages.send(
            user_id=user_id,
            random_id=get_random_id(),
            keyboard=keyboard.get_keyboard(),
            message='Старт'
        )
        return None

    reply_text = event.text
    answer = multi_split(['.', '('], questions_answers[question])[0]
    if reply_text.upper().strip() == answer.upper().strip():
        reply_text = 'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»'
    else:
        reply_text = 'Неправильно… Попробуешь ещё раз?'

    vk_bot.messages.send(
        user_id=event.user_id,
        random_id=get_random_id(),
        message=reply_text,
        keyboard=keyboard.get_keyboard()
    )


def handle_new_question_request(event, vk_bot, redis_session, questions_answers):
    user_id = event.user_id
    question = random.choice(list(questions_answers.items()))[0]
    redis_session.set(user_id, question)
    keyboard = make_keyboard()
    vk_bot.messages.send(
        user_id=user_id,
        random_id=get_random_id(),
        message=f'Новый вопрос: {question}',
        keyboard=keyboard.get_keyboard()
    )


def handle_surrenger(event, vk_bot, redis_session, questions_answers):
    user_id = event.user_id
    question = redis_session.get(user_id)
    answer = multi_split(['.', '('], questions_answers[question])[0]
    keyboard = make_keyboard()
    vk_bot.messages.send(
        user_id=user_id,
        random_id=get_random_id(),
        message=(
            f'Вопрос: {question}\n'
            f'Правильный ответ: {answer}'
        ),
        keyboard=keyboard.get_keyboard()
    )


def handle_score(event, vk_bot, redis_session):
    user_id = event.user_id
    keyboard = make_keyboard()
    vk_bot.messages.send(
        user_id=user_id,
        random_id=get_random_id(),
        message='TODO Показать счёт...',
        keyboard=keyboard.get_keyboard()
    )


def main():
    quiz_files_folder = env.str('QUIZ_FILES_FOLDER')
    vk_token = env.str('VK_APP_TOKEN')
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

    questions_answers = make_questions_answers(quiz_files_folder)

    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.info('VK bot running...')
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if 'Новый вопрос' in event.text:
                handle_new_question_request(
                    event, vk, redis_session, questions_answers)
            elif 'Сдаться' in event.text:
                handle_surrenger(event, vk, redis_session, questions_answers)
            elif 'Мой счёт' in event.text:
                handle_score(event, vk, redis_session)
            elif 'Выйти' in event.text:
                pass
            else:
                handle_solution_attempt(
                    event, vk, redis_session, questions_answers)


if __name__ == '__main__':
    main()
