import json
import requests
from config import headers, headers_for_detail
from loguru import logger

# ______________________________________________________________________________________________________________________
logger.add(
    'logs/debug_log.log',
    format='{time} {level} {message}',
    level='DEBUG',
    rotation='00:00',
    compression='zip'
)


# ______________________________________________________________________________________________________________________
@logger.catch
def get_cities(city_name: str) -> dict[str, str] | str:
    """
        Парсер для поиска городов, подходящих по имени.
    :param city_name: Имя искомого города
    :return: Словарь: {"Название города": ID} или str с ошибкой.
    """
    logger.debug(f'utils.get_cities - принято название города: {city_name}')
    url = "https://hotels4.p.rapidapi.com/locations/v3/search"
    querystring = {"q": city_name, "locale": "en_US", "langid": "1033", "siteid": "300000001"}
    response = requests.get(url, headers=headers, params=querystring)
    logger.debug(f'utils.get_cities - код ответа: {response.status_code}')
    if response.status_code == 200:
        cities = {value["regionNames"]["shortName"]: value["gaiaId"]
                  for value in response.json()["sr"] if value["type"] == "CITY"}
        if cities:
            logger.debug(f'utils.get_cities - возвращено: {cities}')
            return cities
        answer = 'Такого города нет. Проверьте ввод или задайте другой город'
        logger.debug(f'utils.get_cities - возвращено: {answer}')
        return answer
    else:
        answer = 'Ошибка ответа сервера, пожалуйста повторите ввод.'
        logger.debug(f'utils.get_cities - возвращено: {answer}')
        return answer


# ______________________________________________________________________________________________________________________
@logger.catch
def get_details(id: int, headers=headers_for_detail) -> json:
    """
        Вспомогательный парсер для get_hotels. Получает фото и адрес по id отеля.
    :param id: Id отеля
    :param headers: Заголовки запроса
    :return: json
    """
    logger.debug(f'utils.get_details - принят id отеля: {id}')
    url = "https://hotels4.p.rapidapi.com/properties/v2/detail"
    payload = {
        "currency": "USD",
        "eapid": 1,
        "locale": "en_US",
        "siteId": 300000001,
        "propertyId": id
    }
    headers = headers

    response = requests.post(url, json=payload, headers=headers)
    logger.debug(f'utils.get_details - статус код {response.status_code}, возвращаю JSON')
    return response.json()


# ______________________________________________________________________________________________________________________
@logger.catch
def get_hotels(states: dict, headers=headers) -> json:
    """
        Парсер для получения названия, адреса, удаленности от центра, цены и фото отеля.
    :param states: Словарь с состояниями
    :param headers: Заголовки запроса
    :return: список словарей с данными по отелю, для подготовки ответа
    """
    logger.debug(f'utils.get_hotels - приняты состояния пользователя: {states}')
    sort_type = ''
    if states['search_type'] == '/lowprice':
        sort_type = 'PRICE_LOW_TO_HIGH'
        logger.debug(f'utils.get_hotels - команда /lowprice, sort: "{sort_type}"')

    url = "https://hotels4.p.rapidapi.com/properties/v2/list"
    payload = {
        "siteId": 300000001,
        "destination": {"regionId": states['destinationID']},
        "checkInDate": states['checkInDate'],
        "checkOutDate": states['checkOutDate'],
        "rooms": [
            {
                "adults": 2,
                "children": [{"age": 5}, {"age": 7}]
            }
        ],
        "resultsStartingIndex": 0,
        "resultsSize": 10,
        "sort": sort_type
    }
    response = requests.post(url, json=payload, headers=headers)
    logger.debug(f'utils.get_hotels - код ответа: {response.status_code}')
    pre_result = list()

    for hotel_data in response.json()['data']['propertySearch']['properties']:
        details = get_details(hotel_data['id'])
        images_urls_list = list()

        if states['need_photo']:
            images_generator = (image for image in details['data']['propertyInfo']['propertyGallery']['images'])
            for _ in range(states['photo_qty']):
                images_urls_list.append(next(images_generator)['image']['url'])
            logger.debug(f'utils.get_hotels - сформирован images_urls_list')

        pre_result.append({
                    'name': hotel_data['name'],
                    'distance_unit': hotel_data['destinationInfo']['distanceFromDestination']['unit'],
                    'distance_value': hotel_data['destinationInfo']['distanceFromDestination']['value'],
                    'price': hotel_data['price']['lead']['amount'],
                    'code': hotel_data['price']['lead']['currencyInfo']['code'],
                    'address': details['data']['propertyInfo']['summary']['location']['address']['addressLine'],
                    'images': images_urls_list
                    })

    if states['search_type'] == '/lowprice':
        logger.debug(f'utils.get_hotels - возвращаю JSON для /lowprice')
        return pre_result[0:states['hotels_qty']]
    elif states['search_type'] == '/bestdeal':
        result = [data for data in pre_result
                  if float(states['distance_min']) < float(data['distance_value']) < float(states['distance_max'])]
        logger.debug(f'utils.get_hotels - возвращаю JSON для /bestdeal')
        return result[0:states['hotels_qty']]
    elif states['search_type'] == '/highprice':
        result = sorted(pre_result, key=lambda data: data['price'], reverse=True)
        logger.debug(f'utils.get_hotels - возвращаю JSON для /highprice')
        return result[0:states['hotels_qty']]


# ______________________________________________________________________________________________________________________
@logger.catch
def check_data(data: str) -> dict[str, int] | None:
    """
        Функция проверки корректности ввода даты. Возвращает готовый словарь для API или None.
    :param data: Строка с датой
    :return: Словарь для API или None
    """
    logger.debug(f'utils.check_data - получена строка с датой {data}')
    clean_digits = ''.join([i for i in data if i.isdigit()])
    if len(clean_digits) == 8:
        data_dict = {
            "day": int(clean_digits[0:2]),
            "month": int(clean_digits[2:4]),
            "year": int(clean_digits[4:8])
        }
        logger.debug(f'utils.check_data - возвращаю {data_dict}')
        return data_dict
    logger.debug(f'utils.check_data - в строке не 8 цифр, возвращаю None.')
    return None
