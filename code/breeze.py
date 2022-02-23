import requests
import json
from code.configs import (
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


class Breeze(BreezeRequests):

    @classmethod
    def get_contacts(cls, limit=None):
        url = 'people?details=1&limit=10'
        if limit is not None:
            url = f'{url}&limit={limit}'
        response = cls.get(url)

        if response.status_code != 200:
            return False, json.loads(response.content)
        return True, json.loads(response.content)
