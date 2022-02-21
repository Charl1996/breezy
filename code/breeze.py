import requests
from configs import (
    BREEZE_API_URL,
    BREEZE_API_KEY,
)


class BreezeRequests:

    @classmethod
    def headers(cls):
        return {
            'Content-Type': 'application/json',
            'Api-Key': f'{BREEZE_API_KEY}'
        }

    @classmethod
    def get(cls, resource):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=BREEZE_API_URL,
            resource_endpoint=resource
        )
        return requests.get(url, headers=cls.headers())


class Beeze:
    pass
