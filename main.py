from loguru import logger
from telebot import custom_filters, types, TeleBot
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from telebot.types import CallbackQuery, Message, InputMediaPhoto
from models import *
from config import API_token
from project.history_utils import get_history, delete_history, write_history
from utils import get_cities, get_hotels, check_data

state_storage = StateMemoryStorage()
bot = TeleBot(API_token, state_storage=state_storage)

# ______________________________________________________________________________________________________________________
User.create_table()
History.create_table()


# ______________________________________________________________________________________________________________________
logger.add(
    'logs/debug_log.log',
    format='{time} {level} {message}',
    level='DEBUG',
    rotation='00:00',
    compression='zip'
)


# ______________________________________________________________________________________________________________________
class MyStates(StatesGroup):  # хранилище состояний
    city = State()
    destinationID = State()
    hotels_qty = State()
    need_photo = State()
    photo_qty = State()
    checkInDate = State()
    checkOutDate = State()
    search_type = State()
    distance_min = State()
    distance_max = State()


# ______________________________________________________________________________________________________________________
@bot.message_handler(func=lambda message: message.text.lower() in ["/hello_world", "привет", "/start"])
@logger.catch
def start(message: Message):
    """
    Обработчик для приветствия.
    Возвращает описание работы бота и команды.
    :param message: ТГ сообщение
    :return: None
    """
    logger.debug(f'main.start - от {message.from_user.id} получено: {message.text}')
    answer = f'Привет, {message.chat.username}!\n' \
             f'Я - бот агентства Too Easy Travel, который поможет тебе в поиске отелей и хостелов.\n' \
             f'Введите одну из команд:\n' \
             f'/lowprice - для поиска вариантов подешевле\n' \
             f'/highprice - для поиска вариантов подороже\n' \
             f'/bestdeal - для выбора по удаленности от центра города\n' \
             f'/history - для показа истории поиска'
    bot.send_message(message.chat.id, answer)
    logger.debug(f'main.start - для {message.from_user.id} отправлено приветствие')


# ______________________________________________________________________________________________________________________
@bot.message_handler(commands=['lowprice', 'highprice'])
@logger.catch
def get_city_name(message: Message):
    """
    Обработчик команд lowprice и highprice.
    Запрашивает город для команд lowprice и highprice.
    Устанавливает для команд lowprice и highprice -  search_type и city, записывает для них search_type.
    :param message: ТГ сообщение
    :return: None
    """
    logger.debug(f'main.get_city_name - от {message.from_user.id} получено: {message.text}')
    bot.set_state(message.from_user.id, MyStates.search_type, message.chat.id)
    logger.debug(f'main.get_city_name - для {message.from_user.id} установлено состояние search_type')
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['search_type'] = message.text
    logger.debug(f'main.get_city_name - для {message.from_user.id} записано в search_type {message.text}')

    comment = ''
    if message == 'lowprice':
        comment = 'Экономика должна быть экономной.'
    elif message == 'highprice':
        comment = 'Гулять так гулять!'

    answer = f'{comment} Какой город рассматриваем?'
    bot.send_message(message.chat.id, answer)
    logger.debug(f'main.get_city_name - у {message.from_user.id} запрошено название города')
    bot.set_state(message.from_user.id, MyStates.city, message.chat.id)
    logger.debug(f'main.get_city_name - для {message.from_user.id} установлено состояние city')


# ______________________________________________________________________________________________________________________
@bot.message_handler(commands=['bestdeal'])
@logger.catch
def get_distance_min(message: Message):
    """
    Обработчик команды bestdeal.
    Запрашивает минимальное расстояние от центра.
    Устанавливает для bestdeal search_type и distance_min, записывает search_type.
    :param message: ТГ сообщение
    :return: None
    """
    logger.debug(f'main.get_distance_min - от {message.from_user.id} получено {message.text}')
    bot.set_state(message.from_user.id, MyStates.search_type, message.chat.id)
    logger.debug(f'main.get_distance_min - для {message.from_user.id} установлено состояние search_type')
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['search_type'] = message.text
    logger.debug(f'main.get_distance_min - для {message.from_user.id} записано в search_type {message.text}')

    answer = 'Какое минимальное расстояние от центра подходит? (целое число)'
    bot.send_message(message.chat.id, answer)
    logger.debug(f'main.get_distance_min - для {message.from_user.id} отправлен запрос мин расстояния от центра')
    bot.set_state(message.from_user.id, MyStates.distance_min, message.chat.id)
    logger.debug(f'main.get_distance_min - для {message.from_user.id} установлено состояние distance_min')


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.distance_min)
@logger.catch
def get_distance_max(message: Message):
    """
    Обработчик, реагирующий на установку состояния distance_min.
    Запрашивает максимальное расстояние от центра.
    Устанавливает для bestdeal - distance_max, записывает distance_min.
    :param message: ТГ сообщение
    :return: None
    """
    logger.debug(f'main.get_distance_max - от {message.from_user.id} получено {message.text}')
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['distance_min'] = message.text
    logger.debug(f'main.get_distance_max - для {message.from_user.id} записано в distance_min {message.text}')

    answer = 'Какое максимальное расстояние от центра рассматриваем? (целое число)'
    bot.send_message(message.chat.id, answer)
    logger.debug(f'main.get_distance_max - для {message.from_user.id} отправлен запрос макс расстояния от центра')
    bot.set_state(message.from_user.id, MyStates.distance_max, message.chat.id)
    logger.debug(f'main.get_distance_max - для {message.from_user.id} установлено состояние distance_max')


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.distance_max)
@logger.catch
def get_city_name_bestdeal(message: Message):
    """
     Обработчик, реагирующий на установку состояния distance_max.
     Запрашивает название города для bestdeal.
     Устанавливает city для bestdeal, записывает distance_max.
     :param message: ТГ сообщение
     :return: None
     """
    logger.debug(f'main.get_city_name_bestdeal - от {message.from_user.id} получено {message.text}')
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['distance_max'] = message.text
    logger.debug(f'main.get_city_name_bestdeal - для {message.from_user.id} записано в distance_max {message.text}')

    answer = 'Какой город рассматриваем?'
    bot.send_message(message.chat.id, answer)
    logger.debug(f'main.get_city_name_bestdeal - у {message.from_user.id} запрошено название города')
    bot.set_state(message.from_user.id, MyStates.city, message.chat.id)
    logger.debug(f'main.get_city_name_bestdeal - для {message.from_user.id} установлено состояние city')


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.city)
@logger.catch
def get_destination_id(message: Message):
    """
     Обработчик, реагирующий на установку состояния city.
     Предлагает выбрать город из найденных вариантов.
     Устанавливает destinationID, записывает city.
     :param message: ТГ сообщение
     :return: None
     """
    logger.debug(f'main.get_destination_id - от {message.from_user.id} получено {message.text}')
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['city'] = message.text
    logger.debug(f'main.get_destination_id - для {message.from_user.id} записано в city {message.text}')

    cities = get_cities(data['city'])
    if isinstance(cities, dict):
        buttons = types.InlineKeyboardMarkup()
        for key, value in cities.items():
            buttons.add(types.InlineKeyboardButton(text=key, callback_data=value))
        bot.send_message(message.chat.id, "Выберите подходящий город, либо измените ввод:", reply_markup=buttons)
        bot.set_state(message.from_user.id, MyStates.destinationID, message.chat.id)
        logger.debug(f'main.get_destination_id - для {message.from_user.id} сформированы кнопки выбора города')
    else:
        bot.send_message(message.chat.id, cities)


# ______________________________________________________________________________________________________________________
@bot.callback_query_handler(func=lambda call: call.data.isdigit())
@logger.catch
def get_check_in_date(call: CallbackQuery):
    """
     Обработчик, реагирующий на callback (ID города).
     Запрашивает дату заезда.
     Устанавливает checkInDate, записывает destinationID.
     :param call: CallbackQuery
     :return: None
     """
    logger.debug(f'main.get_check_in_date - от {call.from_user.id} получено {call.data}')
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['destinationID'] = call.data
    logger.debug(f'main.get_check_in_date - для {call.from_user.id} записано в destinationID {call.data}')

    answer = "Укажите дату заезда (ДД.ММ.ГГГГ)"
    bot.send_message(call.message.chat.id, answer)
    logger.debug(f'main.get_check_in_date - у {call.from_user.id} запрошена дата заезда')
    bot.set_state(call.from_user.id, MyStates.checkInDate, call.message.chat.id)
    logger.debug(f'main.get_check_in_date - для {call.from_user.id} установлено состояние checkInDate')


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.checkInDate)
@logger.catch
def get_check_out_date(message: Message):
    """
     Обработчик, реагирующий на установку состояния checkInDate.
     Запрашивает дату выезда.
     Устанавливает checkOutDate, записывает checkInDate.
     :param message: ТГ сообщение
     :return: None
     """
    logger.debug(f'main.get_check_out_date - от {message.from_user.id} получено {message.text}')
    if data_dict := check_data(message.text):
        if datetime.now() <= datetime(data_dict['year'], data_dict['month'], data_dict['day']):
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['checkInDate'] = data_dict
            logger.debug(f'main.get_check_out_date - для {message.from_user.id} записано в checkInDate {message.text}')

            answer = 'Укажите дату выезда (ДД.ММ.ГГГГ)'
            bot.send_message(message.chat.id, answer)
            logger.debug(f'main.get_check_out_date - для {message.from_user.id} запрошена дата выезда')
            bot.set_state(message.from_user.id, MyStates.checkOutDate, message.chat.id)
            logger.debug(f'main.get_check_out_date - для {message.from_user.id} установлено состояние checkOutDate')
        else:
            answer = 'Упс, дата заселения должна быть больше текущей.'
            bot.send_message(message.chat.id, answer)
            logger.debug(f'main.get_check_out_date - от {message.from_user.id} получена дата меньше текущей')

    else:
        answer = 'Ну как-так? Дата введена не верно, попробуйте снова (ДД.ММ.ГГГГ)'
        bot.send_message(message.chat.id, answer)


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.checkOutDate)
@logger.catch
def get_hotels_qty(message: Message):
    """
     Обработчик, реагирующий на установку состояния checkOutDate.
     Запрашивает количество отелей.
     Устанавливает hotels_qty, записывает checkInDate.
     :param message: ТГ сообщение
     :return: None
     """
    logger.debug(f'main.get_hotels_qty - от {message.from_user.id} получено {message.text}')
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        check_in_date = data['checkInDate']

    if data_dict := check_data(message.text):
        check_out = datetime(data_dict['year'], data_dict['month'], data_dict['day'])
        check_in = datetime(check_in_date['year'], check_in_date['month'], check_in_date['day'])
        if check_in < check_out:
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['checkOutDate'] = data_dict
            logger.debug(f'main.get_hotels_qty - для {message.from_user.id} записано в checkOutDate {message.text}')

            answer = 'Сколько предложений показать (цифра до 5)'
            bot.send_message(message.chat.id, answer)
            logger.debug(f'main.get_hotels_qty - для {message.from_user.id} запрошено количство отелей.')
            bot.set_state(message.from_user.id, MyStates.hotels_qty, message.chat.id)
            logger.debug(f'main.get_hotels_qty - для {message.from_user.id} установлено состояние hotels_qty')
        else:
            answer = 'Упс, дата выезда должна быть больше даты заселения.'
            bot.send_message(message.chat.id, answer)
            logger.debug(f'main.get_hotels_qty - {message.from_user.id} указал дату выезда, меньшую даты заселения')

    else:
        answer = 'Ну как-так? Дата введена не верно, попробуйте снова (ДД.ММ.ГГГГ)'
        bot.send_message(message.chat.id, answer)


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.hotels_qty)
@logger.catch
def get_need_photo(message: Message):
    """
     Обработчик, реагирующий на установку состояния hotels_qty.
     Запрашивает необходимость загрузки фото.
     Устанавливает need_photo, записывает hotels_qty.
     :param message: ТГ сообщение
     :return: None
     """
    logger.debug(f'main.get_need_photo - от {message.from_user.id} получено {message.text}')
    if message.text.isdigit() and int(message.text) <= 5:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['hotels_qty'] = int(message.text)
        logger.debug(f'main.get_need_photo - для {message.from_user.id} записано в hotels_qty {message.text}')

        answer = 'Загрузить фото? (да/нет).'
        bot.send_message(message.chat.id, answer)
        logger.debug(f'main.get_need_photo - для {message.from_user.id} запрошено нужны ли фотографии')
        bot.set_state(message.from_user.id, MyStates.need_photo, message.chat.id)
        logger.debug(f'main.get_need_photo - для {message.from_user.id} установлено состояние need_photo')
    else:
        answer = 'Такого от вас я не ожидал... Укажите число до 5.'
        bot.send_message(message.chat.id, answer)
        logger.debug(f'main.get_need_photo - {message.from_user.id} ошибся с вводом количества фото')


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.need_photo)
@logger.catch
def get_photo_qty(message: Message):
    """
     Обработчик, реагирующий на установку состояния need_photo.
     Если фото нужны - запрашивает их количество.
     Устанавливает photo_qty если нужны фотографии, записывает need_photo, записывает историю поиска.
     Отправляет результат поиска если не нужны фотографии, удаляет состояния.
     :param message: ТГ сообщение
     :return: None
     """
    logger.debug(f'main.get_photo_qty - от {message.from_user.id} получено {message.text}')
    if message.text.lower() == 'да':
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['need_photo'] = True
        logger.debug(f'main.get_photo_qty - для {message.from_user.id} записано в need_photo True')

        answer = 'Сколько фото показать (цифра до 5)?'
        bot.send_message(message.chat.id, answer)
        logger.debug(f'main.get_photo_qty - для {message.from_user.id} запрошено количество фото')
        bot.set_state(message.from_user.id, MyStates.photo_qty, message.chat.id)
        logger.debug(f'main.get_photo_qty - для {message.from_user.id} установлено состояние photo_qty')
    elif message.text.lower() == 'нет':
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['need_photo'] = False
        logger.debug(f'main.get_photo_qty - для {message.from_user.id} записано в need_photo False')

        answer = "Собираю данные..."
        bot.send_message(message.chat.id, answer)
        result = get_hotels(data)
        if len(result) > 0:
            for hotel_data in result:
                answer = f"Название: {hotel_data['name']}\n" \
                         f"Адрес: {hotel_data['address']}\n" \
                         f"До центра: {hotel_data['distance_value']} {hotel_data['distance_unit']}\n" \
                         f"Цена: {hotel_data['price']} {hotel_data['code']}\n"
                bot.send_message(message.chat.id, answer)
                logger.debug(f'main.get_photo_qty - для {message.from_user.id} отправлен результат')
        else:
            bot.send_message(message.chat.id, f' Ни чего не нашлось...')
            logger.debug(f'main.get_photo_qty - для {message.from_user.id} ни чего не найдено')

        bot.send_message(message.chat.id, f' Введите:\n'
                                          f'/lowprice - для поиска вариантов подешевле\n'
                                          f'/highprice - для поиска вариантов подороже\n'
                                          f'/bestdeal - для выбора по удаленности от центра города\n'
                                          f'/history - для показа истории поиска')
        write_history(message.from_user.id, data, result)
        logger.debug(f'main.get_photo_qty - для {message.from_user.id} новая запись в истории')
        bot.delete_state(message.from_user.id, message.chat.id)
        logger.debug(f'main.get_photo_qty - для {message.from_user.id} удалены состояния')

    else:
        answer = "Что-что??? Напишите да/нет."
        bot.send_message(message.chat.id, answer)
        logger.debug(f'main.get_photo_qty - от {message.from_user.id} получен не корректный ответ о загрузке фото')


# ______________________________________________________________________________________________________________________
@bot.message_handler(state=MyStates.photo_qty)
@logger.catch
def full_answer(message: Message):
    """
      Обработчик, реагирующий на установку состояния photo_qty.
      Записывает photo_qty.
      Отправляет результат поиска если нужны фотографии, удаляет состояния, записывает историю поиска.
      :param message: ТГ сообщение
      :return: None
      """
    logger.debug(f'main.full_answer - от {message.from_user.id} получено {message.text}')
    if message.text.isdigit() and int(message.text) <= 5:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['photo_qty'] = int(message.text)
        logger.debug(f'main.full_answer - для {message.from_user.id} записано в photo_qty {message.text}')

        answer = "Собираю данные..."
        bot.send_message(message.chat.id, answer)
        result = get_hotels(data)
        if len(result) > 0:
            for hotel_data in result:
                media = list()
                answer = f"Название: {hotel_data['name']}\n" \
                         f"Адрес: {hotel_data['address']}\n" \
                         f"До центра: {hotel_data['distance_value']} {hotel_data['distance_unit']}\n" \
                         f"Цена: {hotel_data['price']} {hotel_data['code']}\n"
                for i, link in enumerate(hotel_data['images'], 1):
                    if i == 1:
                        media.append(InputMediaPhoto(media=link, caption=answer))
                    else:
                        media.append(InputMediaPhoto(media=link))
                bot.send_media_group(message.chat.id, media)
                logger.debug(f'main.full_answer - для {message.from_user.id} отправлен результат с фото')

        else:
            bot.send_message(message.chat.id, f' Ни чего не нашлось...')
            logger.debug(f'main.full_answer - для {message.from_user.id} ни чего не найдено')

        bot.send_message(message.chat.id, f' Введите:\n'
                                          f'/lowprice - для поиска вариантов подешевле\n'
                                          f'/highprice - для поиска вариантов подороже\n'
                                          f'/bestdeal - для выбора по удаленности от центра города\n'
                                          f'/history - для показа истории поиска')
        write_history(message.from_user.id, data, result)
        logger.debug(f'main.full_answer - для {message.from_user.id} новая запись в истории')
        bot.delete_state(message.from_user.id, message.chat.id)
        logger.debug(f'main.full_answer - для {message.from_user.id} удалены состояния')
    else:
        answer = 'Такого от вас я не ожидал... Укажите число до 5.'
        bot.send_message(message.chat.id, answer)


# ______________________________________________________________________________________________________________________
@bot.message_handler(commands=['history'])
@logger.catch
def show_history(message: Message):
    """
      Обработчик, реагирующий на команду history.
      Выводит историю в чат, если она есть в базе данных.
      :param message: ТГ сообщение
      :return: None
      """
    logger.debug(f'main.show_history - от {message.from_user.id} получено {message.text}')
    history = get_history(message.from_user.id)
    if len(history) > 0:
        for i in history:
            bot.send_message(message.chat.id, f'{i.command}:\n{i.value}')
        bot.send_message(message.chat.id, 'Для очистки истории используйте команду /delete')
        logger.debug(f'main.show_history - для {message.from_user.id} отправлена история поиска')
    else:
        bot.send_message(message.chat.id, 'В истории нет записей.')
        logger.debug(f'main.show_history - для {message.from_user.id} нет записей в истории')


# ______________________________________________________________________________________________________________________
@bot.message_handler(commands=['delete'])
@logger.catch
def clean_history(message: Message):
    """
      Обработчик, реагирующий на команду delete.
      Удаляет историю текущего пользователя.
      :param message: ТГ сообщение
      :return: None
      """
    logger.debug(f'main.clean_history - для {message.from_user.id} получено {message.text}')
    if delete_history(message.from_user.id):
        bot.send_message(message.chat.id, 'История очищена!')
        bot.send_message(message.chat.id, f' Введите:\n'
                                          f'/lowprice - для поиска вариантов подешевле\n'
                                          f'/highprice - для поиска вариантов подороже\n'
                                          f'/bestdeal - для выбора по удаленности от центра города\n')
    else:
        bot.send_message(message.chat.id, 'Что-то пошло не так... ')
        logger.debug(f'main.clean_history - для {message.from_user.id} не удается удалить историю')


# ______________________________________________________________________________________________________________________
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.add_custom_filter(custom_filters.IsDigitFilter())

bot.polling(none_stop=True)
