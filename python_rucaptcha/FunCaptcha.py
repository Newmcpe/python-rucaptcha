import requests
import time
import asyncio
import aiohttp
from requests.adapters import HTTPAdapter
from urllib3.exceptions import MaxRetryError

from .config import url_request_2captcha, url_response_2captcha, url_request_rucaptcha, url_response_rucaptcha, app_key, \
    JSON_RESPONSE
from .errors import RuCaptchaError


class FunCaptcha:
    """
	Класс служит для работы с FunCaptcha.
	Для работы потребуется передать ключ от РуКапчи, затем ключ сайта(подробности его получения в описании на сайте)
	И так же ссылку на сайт.
	"""

    def __init__(self, rucaptcha_key: str, service_type: str='2captcha', sleep_time: int=15, **kwargs):
        """
		Инициализация нужных переменных.
		:param rucaptcha_key:  АПИ ключ капчи из кабинета пользователя
		:param service_type: URL с которым будет работать программа, возможен вариант "2captcha"(стандартный)
                             и "rucaptcha"
		:param sleep_time: Вермя ожидания решения капчи
		:param kwargs: Для передачи дополнительных параметров
		"""
        # проверка введённого времени и изменение если минимальный порог нарушен
        if sleep_time < 15:
            raise ValueError(f'\nПараметр `sleep_time` должен быть не менее 10(рекомендуемое - 20 секунд). '
                             f'\n\tВы передали - {sleep_time}')
        self.sleep_time = sleep_time

        # выбираем URL на который будут отпраляться запросы и с которого будут приходить ответы
        if service_type == '2captcha':
            self.url_request = url_request_2captcha
            self.url_response = url_response_2captcha
        elif service_type == 'rucaptcha':
            self.url_request = url_request_rucaptcha
            self.url_response = url_response_rucaptcha
        else:
            raise ValueError('Передан неверный параметр URL-сервиса капчи! Возможные варинты: `rucaptcha` и `2captcha`.'
                             'Wrong `service_type` parameter. Valid formats: `rucaptcha` or `2captcha`.')

        # пайлоад POST запроса на отправку капчи на сервер
        self.post_payload = {"key": rucaptcha_key,
                             'method': 'funcaptcha',
                             "json": 1,
                             "soft_id": app_key}
        # Если переданы ещё параметры - вносим их в payload
        if kwargs:
            for key in kwargs:
                self.post_payload.update({key: kwargs[key]})

        # пайлоад GET запроса на получение результата решения капчи
        self.get_payload = {'key': rucaptcha_key,
                            'action': 'get',
                            'json': 1,
                            }
        # результат возвращаемый методом *captcha_handler*
        self.result = JSON_RESPONSE

        # создаём сессию
        self.session = requests.Session()
        # выставляем кол-во попыток подключения к серверу при ошибке
        self.session.mount('http://', HTTPAdapter(max_retries=5))

    # Работа с капчей
    def captcha_handler(self, public_key: str, page_url: str):
        '''
		Метод отвечает за передачу данных на сервер для решения капчи
		:param site_key: Ключ сайта
		:param page_url: Ссылка на страницу на которой находится капча
    	:return: В качестве ответа передаётся JSON с данными для решения капчи
		'''
        # добавляем в пайлоад параметры капчи переданные пользователем
        self.post_payload.update({'publickey': public_key,
                                  'pageurl': page_url})
        # получаем ID капчи
        captcha_id = self.session.post(self.url_request, data=self.post_payload).json()

        # если вернулся ответ с ошибкой то записываем её и возвращаем результат
        if captcha_id['status'] is 0:
            self.result.update({'error': True,
                                'errorBody': RuCaptchaError().errors(captcha_id['request'])
                                }
                               )
            return self.result
        # иначе берём ключ отправленной на решение капчи и ждём решения
        else:
            captcha_id = captcha_id['request']
            # вписываем в taskId ключ отправленной на решение капчи
            self.result.update({"taskId": captcha_id})
            # обновляем пайлоад, вносим в него ключ отправленной на решение капчи
            self.get_payload.update({'id': captcha_id})

        # Ожидаем решения капчи 20 секунд
        # Ожидаем решения капчи
        time.sleep(self.sleep_time)
        while True:
            try:
                # отправляем запрос на результат решения капчи, если не решена ожидаем
                captcha_response = self.session.post(self.url_response, data=self.get_payload)

                # если капча ещё не решена - ожидаем
                if captcha_response.json()['request'] == 'CAPCHA_NOT_READY':
                    time.sleep(self.sleep_time)

                # при ошибке во время решения
                elif captcha_response.json()["status"] == 0:
                    self.result.update({'error': True,
                                        'errorBody': RuCaptchaError().errors(captcha_response.json()["request"])
                                        }
                                       )
                    return self.result

                # при решении капчи
                elif captcha_response.json()["status"] == 1:
                    self.result.update({
                                        'captchaSolve': captcha_response.json()['request']
                                        }
                                       )
                    return self.result

            except (TimeoutError, ConnectionError, MaxRetryError) as error:
                    self.result.update({'error': True,
                                        'errorBody': {
                                            'text': error
                                            }
                                        }
                                       )
                    return self.result

            except Exception as error:
                    self.result.update({'error': True,
                                        'errorBody': {
                                            'text': error
                                            }
                                        }
                                       )
                    return self.result


# асинхронный метод для решения FunCaptcha
class aioFunCaptcha:
    """
    Класс служит для работы с FunCaptcha.
    Для работы потребуется передать ключ от РуКапчи, затем ключ сайта(подробности его получения в описании на сайте)
    И так же ссылку на сайт.
    """

    def __init__(self, rucaptcha_key: str, service_type: str='2captcha', sleep_time: int=15, **kwargs):
        """
        Инициализация нужных переменных.
        :param rucaptcha_key:  АПИ ключ капчи из кабинета пользователя
        :param service_type: URL с которым будет работать программа, возможен вариант "2captcha"(стандартный)
                             и "rucaptcha"
        :param sleep_time: Вермя ожидания решения капчи
        :param kwargs: Для передачи дополнительных параметров
        """
        # проверка введённого времени и изменение если минимальный порог нарушен
        if sleep_time < 15:
            raise ValueError(f'\nПараметр `sleep_time` должен быть не менее 10(рекомендуемое - 20 секунд). '
                             f'\n\tВы передали - {sleep_time}')
        self.sleep_time = sleep_time

        # выбираем URL на который будут отпраляться запросы и с которого будут приходить ответы
        if service_type == '2captcha':
            self.url_request = url_request_2captcha
            self.url_response = url_response_2captcha
        elif service_type == 'rucaptcha':
            self.url_request = url_request_rucaptcha
            self.url_response = url_response_rucaptcha
        else:
            raise ValueError('Передан неверный параметр URL-сервиса капчи! Возможные варинты: `rucaptcha` и `2captcha`.'
                             'Wrong `service_type` parameter. Valid formats: `rucaptcha` or `2captcha`.')

        # пайлоад POST запроса на отправку капчи на сервер
        self.post_payload = {"key": rucaptcha_key,
                             'method': 'funcaptcha',
                             "json": 1,
                             "soft_id": app_key}
        # Если переданы ещё параметры - вносим их в payload
        if kwargs:
            for key in kwargs:
                self.post_payload.update({key: kwargs[key]})

        # пайлоад GET запроса на получение результата решения капчи
        self.get_payload = {'key': rucaptcha_key,
                            'action': 'get',
                            'json': 1,
                            }
        # результат возвращаемый методом *captcha_handler*
        self.result = JSON_RESPONSE

    # Работа с капчей
    async def captcha_handler(self, public_key: str, page_url: str):
        '''
    	Метод отвечает за передачу данных на сервер для решения капчи
		:param site_key: Ключ сайта
    	:param page_url: Ссылка на страницу на которой находится капча
    	:return: В качестве ответа передаётся JSON с данными для решения капчи
		'''
        self.post_payload.update({'publickey': public_key,
                                  'pageurl': page_url})
        # получаем ID капчи
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url_request, data=self.post_payload) as resp:
                captcha_id = await resp.json()

        # если вернулся ответ с ошибкой то записываем её и возвращаем результат
        if captcha_id['status'] is 0:
            self.result.update({'error': True,
                                'errorBody': RuCaptchaError().errors(captcha_id['request'])
                                }
                               )
            return self.result
        # иначе берём ключ отправленной на решение капчи и ждём решения
        else:
            captcha_id = captcha_id['request']
            # вписываем в taskId ключ отправленной на решение капчи
            self.result.update({"taskId": captcha_id})
            # обновляем пайлоад, вносим в него ключ отправленной на решение капчи
            self.get_payload.update({'id': captcha_id})

        # Ожидаем решения капчи
        await asyncio.sleep(self.sleep_time)
        # отправляем запрос на результат решения капчи, если не решена ожидаем
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.post(self.url_response, data=self.get_payload) as resp:
                        captcha_response = await resp.json()

                        # если капча ещё не решена - ожидаем
                        if captcha_response['request'] == 'CAPCHA_NOT_READY':
                            await asyncio.sleep(self.sleep_time)

                        # при ошибке во время решения
                        elif captcha_response["status"] == 0:
                            self.result.update({'error': True,
                                                'errorBody': RuCaptchaError().errors(captcha_response["request"])
                                                }
                                               )
                            return self.result

                        # при успешном решении капчи
                        elif captcha_response["status"] == 1:
                            self.result.update({
                                                'captchaSolve': captcha_response['request']
                                                }
                                               )
                            return self.result

                except Exception as error:
                    self.result.update({'error': True,
                                        'errorBody': {
                                            'text': error
                                            }
                                        }
                                       )
                    return self.result
