import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv

from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
TIMESTAMP: int = int(time.time())

HOMEWORK_STATUSES: dict = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=(
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(filename='main.log', encoding='UTF-8'),
    )
)


def send_message(bot, message):
    """Функция отправки сообщения в чат телеграм."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.info(f'В телеграм отправлено сообщение: "{message}"')


def get_api_answer(current_timestamp):
    """Функция получения ответа от API."""
    logging.info('Запрос к ЯП передан')
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT,
                            headers=HEADERS,
                            params=params)
    if response.status_code != HTTPStatus.OK:
        logging.error('Нет ответа от сервера')
        raise ConnectionError('Нет ответа от сервера')
    else:
        return response.json()


def check_response(response):
    """Запрос ответа от API ЯП."""
    if isinstance(response, dict):
        if 'homeworks' in response.keys():
            homeworks = response.get('homeworks')
            if isinstance(homeworks, list):
                return homeworks
            else:
                raise TypeError('Формат homeworks не соответствует ожиданию')
        else:
            raise KeyError('Нут такого ключа в словаре')
    else:
        raise TypeError('Формат response не соответствует ожиданию')


def parse_status(homework):
    """Парсинг названия домашней работы и ее статуса."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка корректности переменных окружения."""
    if not (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return False
    return True


def main():
    """Основная логика работы бота."""
    current_timestamp = TIMESTAMP
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    tmp_status = 'reviewing'
    tmp_message = ''
    while True:
        if check_tokens():
            response = get_api_answer(current_timestamp)
            try:
                homework = check_response(response)[0]
                if tmp_status != homework.get('status'):
                    try:
                        message = parse_status(homework)
                        if tmp_message != message:
                            send_message(bot, message)
                        time.sleep(RETRY_TIME)
                        tmp_status = homework.get('status')
                    except Exception as error:
                        message = f'Сбой в работе программы: {error}'
                        logging.error(message)
                        send_message(bot, message)
                    except IndexError:
                        logging.info('Ответ от API - пустой список')
                        time.sleep(RETRY_TIME)
                logging.info('Статус работы не изменился, следующий запрос '
                             'через 10 минут')
                time.sleep(RETRY_TIME)
            except IndexError:
                logging.error('Список пуст')
                time.sleep(RETRY_TIME)
        else:
            logging.critical('Сбой в работе программы: Эндпоинт '
                             '[https://practicum.yandex.ru/api/user_api/'
                             'homework_statuses/](https://'
                             'practicum.yandex.ru/api/user_api/'
                             'homework_statuses/) недоступен. '
                             'Код ответа API: 404'
                             )
            break


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    main()
