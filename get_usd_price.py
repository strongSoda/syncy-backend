# Reference
# 1. Dashboard: https://pro.coinmarketcap.com/account/
# 2. Docs: https://coinmarketcap.com/api/documentation/v1/#operation/getV1ToolsPriceconversion
# 3. Info: Email: strongsoda2@gmail.com, Password: Suggested one, look in passwords manager 

from decimal import Decimal
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json

url = 'https://pro-api.coinmarketcap.com/v1/tools/price-conversion'

def get_usd_price(price, currency):
    parameters = {
    'symbol': 'USD',
    'convert':currency,
    'amount': Decimal(price),
    }
    headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': 'f6b7e573-116c-4661-8559-91926373d257',
    }

    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        usd_price = round(data['data']['quote'][currency]['price'], 6)
        print('$$$', data)
        return usd_price
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)