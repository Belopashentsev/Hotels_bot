import json

from loguru import logger
from peewee import SelectQuery
from models import *


# ______________________________________________________________________________________________________________________
def write_history(user_id: int, states: dict, result: json) -> None:
    """
    Функция записи истории в БД
    :param user_id: TG id пользователя, используется как первичный ключ
    :param states: состояния пользователя, для получения команды
    :param result: список словарей с данными по найденным отелям
    :return: None
    """
    User.get_or_create(user_id=user_id)
    answer = ''
    for i, hotel_data in enumerate(result, 1):
        answer += f"#{i} Название: {hotel_data['name']}\n" \
                 f"Адрес: {hotel_data['address']}\n" \
                 f"До центра: {hotel_data['distance_value']} {hotel_data['distance_unit']}\n" \
                 f"Цена: {hotel_data['price']} {hotel_data['code']}\n\n"
    History.create(command=states['search_type'], value=answer, user=User[user_id])
    logger.debug(f'history_utils.write_history - новая запись в истории {user_id}')


# ______________________________________________________________________________________________________________________
def get_history(user_id: int) -> SelectQuery:
    """
    Функция получения истории запросов пользователя
    :param user_id: TG id пользователя
    :return: SelectQuery
    """
    logger.debug(f'history_utils.get_history - получен запрос на получение истории пользователя {user_id}')
    history = History.select().join(User).where(User.user_id == user_id)
    logger.debug(f'history_utils.get_history - возвращена история поиска для {user_id}')
    return history


# ______________________________________________________________________________________________________________________
def delete_history(user_id: int) -> bool:
    """
    Функция удаления истории запросов пользователя
    :param user_id: TG id пользователя
    :return: True при успешном удалении истории
    """
    logger.debug(f'history_utils.delete_history - получен запрос на удаление истории пользователя {user_id}')
    User[user_id].delete_instance()
    logger.debug(f'history_utils.delete_history - удалена история поиска для {user_id}')
    return True
