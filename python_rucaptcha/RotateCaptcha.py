import requests
import time
import tempfile
from urllib3.exceptions import MaxRetryError
from requests.adapters import HTTPAdapter

from .config import url_request_2captcha, url_response_2captcha, url_request_rucaptcha, url_response_rucaptcha, app_key, \
    JSON_RESPONSE
from .errors import RuCaptchaError


class RotateCaptcha:
    def __init__(self, rucaptcha_key: str, service_type: str='2captcha', sleep_time: int=5):
        '''
        Инициализация нужных переменных, создание папки для изображений и кэша
        После завершения работы - удалются временные фалйы и папки
        :param rucaptcha_key:  АПИ ключ капчи из кабинета пользователя
        :param service_type: Тип сервиса через который будет работать билиотека. Доступны `rucaptcha` или `2captcha`
        :param sleep_time: Вермя ожидания решения капчи
        '''

        if sleep_time < 5:
            raise ValueError(f'Параметр `sleep_time` должен быть не менее 10. Вы передали - {sleep_time}')
        self.sleep_time = sleep_time

        # пайлоад POST запроса на отправку капчи на сервер
        self.post_payload = {"key": rucaptcha_key,
                             'method': 'rotatecaptcha',
                             "json": 1,
                             "soft_id": app_key}

        # пайлоад GET запроса на получение результата решения капчи
        self.get_payload = {'key': rucaptcha_key,
                            'action': 'get',
                            'json': 1,
                            }

        if service_type == '2captcha':
            self.url_request = url_request_2captcha
            self.url_response = url_response_2captcha
        elif service_type == 'rucaptcha':
            self.url_request = url_request_rucaptcha
            self.url_response = url_response_rucaptcha
        else:
            raise ValueError('Передан неверный параметр URL-сервиса капчи! Возможные варинты: `rucaptcha` и `2captcha`.'
                             'Wrong `service_type` parameter. Valid formats: `rucaptcha` or `2captcha`.')

        # результат возвращаемый методом *captcha_handler*
        self.result = JSON_RESPONSE

        # создаём сессию
        self.session = requests.Session()
        # выставляем кол-во попыток подключения к серверу при ошибке
        self.session.mount('http://', HTTPAdapter(max_retries=5))

    # Работа с капчёй
    def captcha_handler(self, captcha_link: str):
        '''
        Метод получает от вас ссылку на изображение, скачивает его, отправляет изображение на сервер
        RuCaptcha, дожидается решения капчи и вовзращает вам результат
        :param captcha_link: Ссылка на изображение
        :return: Ответ на капчу
        '''
        # Скачиваем изображение
        content = self.session.get(captcha_link).content
        with tempfile.NamedTemporaryFile(suffix='.jpg') as out:
            out.write(content)
            captcha_image = open(out.name, 'rb')
            # Отправляем изображение файлом
            files = {'file': captcha_image}
            # Отправляем на рукапча изображение капчи и другие парметры,
            # в результате получаем JSON ответ с номером решаемой капчи и получая ответ - извлекаем номер
            captcha_id = self.session.post(self.url_request, data=self.post_payload, files=files).json()

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

