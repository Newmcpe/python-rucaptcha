from python_rucaptcha import RuCaptchaControl

"""
Этот пример показывает работу модуля управления аккаунтом RuCaptcha.
Присутствует возможность получить информацию о балансе средств и отправить жалобу на неверно решённую капчу.
"""
# Введите ключ от рукапчи из своего аккаунта
RUCAPTCHA_KEY = ""

# пример получения информации о балансе
answer = RuCaptchaControl.RuCaptchaControl(rucaptcha_key = RUCAPTCHA_KEY).additional_methods(action = 'getbalance')

"""
answer - это JSON строка с соответствующими полями:

serverAnswer - ответ сервера при использовании RuCaptchaControl(баланс/жалобы и т.д.)
taskId - находится Id задачи на решение капчи, можно использовать при жалобах и прочем,
error - False - если всё хорошо, True - если есть ошибка,
errorBody - полная информация об ошибке: 
    {
        text - Развернётое пояснение ошибки
        id - уникальный номер ошибка в ЭТОЙ бибилотеке
    }
"""

if not answer['error']:
    print("Your balance is: ", answer['serverAnswer'], " rub.")

elif answer['error']:
    # Тело ошибки, если есть
    print(answer['errorBody'])


# Пример отправки жалобы на неправильно решённую капчу под ID "666"
wrong_captcha_id = 666

answer = RuCaptchaControl.RuCaptchaControl(rucaptcha_key = RUCAPTCHA_KEY).additional_methods(action = 'reportbad',
                                                                                             id = wrong_captcha_id)

# Если заявка принята
if not answer['error']:
    print("Заявка принята.")

# Если возникла ошибка
elif answer['error']:
    print(answer['errorBody'])

"""
Возможны следующие варианты 'action':
getbalance - получить ваш баланс
get - получить ответы на множество капч с помощью одного запроса. Требует указания параметра ids.
get2 - получить стоимость решения отправленной капчи и ответ на нее. Требует указания ID капчи в параметре id

А так же дополнительные параметры
ids	Строка	-	ID ваших капч, разделенные запятыми.
id	Строка	-	ID вашей капчи.

При action = 'reportbad', id - ID неверно решенной капчи и является обязательным параметром.

Подробней обо всех возможных параметрах и их применении:
https://rucaptcha.com/api-rucaptcha#complain
"""
