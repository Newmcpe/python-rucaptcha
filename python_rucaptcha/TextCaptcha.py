import requests
import time
from urllib3.exceptions import MaxRetryError
from requests.adapters import HTTPAdapter

from .config import url_request_2captcha, url_response_2captcha, url_request_rucaptcha, url_response_rucaptcha, app_key, \
    JSON_RESPONSE
from .errors import RuCaptchaError


class TextCaptcha:
    def __init__(self, rucaptcha_key: str, sleep_time: int=5, service_type: str='2captcha', **kwargs):
        if sleep_time < 5:
            raise ValueError(f'Параметр `sleep_time` должен быть не менее 10. Вы передали - {sleep_time}')
        self.sleep_time = sleep_time
        # пайлоад POST запроса на отправку капчи на сервер
        self.post_payload = {"key": rucaptcha_key,
                             "method": "post",
                             "json": 1,
                             "soft_id": app_key,
                             }
        # Если переданы ещё параметры - вносим их в payload
        if kwargs:
            for key in kwargs:
                self.post_payload.update({key: kwargs[key]})

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

    def captcha_handler(self, captcha_text: str):
        # Создаём пайлоад, вводим ключ от сайта, выбираем метод ПОСТ и ждём ответа. в JSON-формате
        self.post_payload.update({"textcaptcha": captcha_text})
        # Отправляем на рукапча текст капчи и ждём ответа
        #  в результате получаем JSON ответ с номером решаемой капчи
        captcha_id = self.session.post(self.url_request,
                                   data=self.post_payload).json()

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
