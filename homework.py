import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

from exceptions import ConnectionError, ObjectIsNoneError, TelegramError, \
    WrongAPIResponseCodeError

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME: int = int(os.getenv('RETRY_TIME', 600))
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
TIMESTAMP: int = 1666340679

HOMEWORK_VERDICTS: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Функция отправки сообщения в чат телеграм."""
    try:
        logging.info('Отправка сообщения в телеграм')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except telegram.error.TelegramError as error:
        message = f'Ошибка отправки сообщения в телеграм, {error}'
        raise TelegramError(message)
    logging.info(f'В телеграм отправлено сообщение: "{message}"')


def get_api_answer(current_timestamp):
    """Функция получения ответа от API."""
    try:
        logging.info('Передача запроса к ЯП')
        timestamp = current_timestamp
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code != HTTPStatus.OK:
            raise WrongAPIResponseCodeError(f'Ответ от сервера не '
                                            f'соответствует ожиданию: '
                                            f'({response.status_code}, '
                                            f'{response.text}) ')
        return response.json()
    except Exception as error:
        raise ConnectionError(f'Ответ от сервера не соответствует ожиданию: '
                              f'{error}')



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
        if homework_name is None:
            raise ObjectIsNoneError('В ответе сервера нет имени работы')
        if homework_status is None:
            raise ObjectIsNoneError('В ответе сервера нет статуса работы')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except IndexError as error:
        raise IndexError(error)


def check_tokens():
    """Проверка корректности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Проблема с переменными окружения. Эндпоинт ЯП API'
                         ' не отвечает')
        sys.exit('Проблема с переменными окружения.')
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
