import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME: int = int(os.getenv('RETRY_TIME', 600))
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
TIMESTAMP: int = 1666155383

HOMEWORK_VERDICTS: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправки сообщения в чат телеграм."""
    logging.info('Отправка сообщения в телеграм')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError:
        raise telegram.error.TelegramError
    logging.info(f'В телеграм отправлено сообщение: "{message}"')


def get_api_answer(current_timestamp):
    """Функция получения ответа от API."""
    logging.info('Передача запроса к ЯП')
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT,
                            headers=HEADERS,
                            params=params)
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Ответ от сервера не соответствует ожиданию: '
                      f'({response.status_code}, {response.text}')
        raise ConnectionError('Ответ от сервера не соответствует ожиданию')
    return response.json()


def check_response(response):
    """Запрос ответа от API ЯП."""
    logging.info('Начат процесс проверки ответа сервера ЯП')
    if isinstance(response, dict):
        if 'homeworks' in response.keys():
            homeworks = response.get('homeworks')
            if isinstance(homeworks, list):
                return homeworks
            raise TypeError('Формат homeworks не соответствует ожиданию')
        raise KeyError('Нут такого ключа в словаре')
    raise TypeError('Формат response не соответствует ожиданию')


def parse_status(homework):
    """Парсинг названия домашней работы и ее статуса."""
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except IndexError as error:
        logging.error(error)


def check_tokens():
    """Проверка корректности переменных окружения."""
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens():
        current_timestamp = TIMESTAMP
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        tmp_status = 'reviewing'
        tmp_message = ''
        while True:
            response = get_api_answer(current_timestamp)
            try:
                homework = check_response(response)[0]
                if tmp_status != homework.get('status'):
                    message = parse_status(homework)
                    tmp_status = homework.get('status')
                    if tmp_message != message:
                        send_message(bot, message)
                else:
                    logging.info('Статус работы не изменился, следующий запрос'
                                 ' через 10 минут')
            except IndexError:
                logging.info('Ответ от API - пустой список. '
                             'Работа еще не взята на проверку.')
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)
                send_message(bot, message)
            finally:
                time.sleep(RETRY_TIME)
    else:
        sys.exit('Проблема с переменными окружения. '
                 'Эндпоинт ЯП API не отвечает')


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    FORMAT = '%(asctime)s - %(levelname)s - %(funcName)s - ' \
             'line %(lineno)d - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=FORMAT,
        handlers=(
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(filename='main.log',
                                encoding='UTF-8'),
        )
    )
    main()
