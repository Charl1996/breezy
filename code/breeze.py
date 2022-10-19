import requests
import json

from datetime import datetime
from configs import (
    BREEZE_API_URL,
    BREEZE_API_KEY,
)
from logger import log


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

    LOGGER_ID = 'Breeze'

    @classmethod
    def get_contacts(cls):
        try:
            log(f'{cls.LOGGER_ID} get_contacts: retrieving tags')
            tags = cls._get_tags()
        except Exception as e:
            log(f'{cls.LOGGER_ID} get_contacts: something went wrong retrieving tags: {e}')
            return False, None, None

        try:
            log(f'{cls.LOGGER_ID} get_contacts: retrieving people')
            people_list = cls._get_people(detail=True)
        except Exception as e:
            log(f'{cls.LOGGER_ID} get_contacts: something went wrong retrieving people: {e}')
            return False, None, None

        people_list_with_tags = []
        for person in people_list:
            p = cls._parse_person_fields(person)
            people_list_with_tags.append(p)

        tags_names = []
        log(f'{cls.LOGGER_ID} get_contacts: updating people tags')

        for tag in tags:
            people = cls._get_users_by_tag_id(tag['id'])
            people_list_with_tags = cls._update_people_in_list_with_tag(people, people_list_with_tags, tag['name'])
            tags_names.append(tag['name'])

        return True, people_list_with_tags, tags_names

    @classmethod
    def _update_people_in_list_with_tag(cls, tags_people, people_list, tag_name):
        for tag_person in tags_people:
            for index, p in enumerate(people_list):
                if p.get('id', '') == tag_person['id']:
                    current_tags = p.get('tags') or []
                    p['tags'] = current_tags + [tag_name]
                    people_list[index] = p

        return people_list

    @classmethod
    def _parse_person_fields(cls, person):
        def _age(birth_date):
            if not birth_date:
                return ''
            born = datetime.strptime(f'{birth_date} 00:00:00', '%Y-%m-%d %H:%M:%S')
            today = datetime.today()
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        def _mobile(phone_list):
            for item in phone_list:
                if item['phone_type'] == 'mobile':
                    return item['phone_number']
            return ''

        def _email(email_list):
            for item in email_list:
                if item['field_type'] == 'email_primary':
                    return item['address']
            return ''

        parsed_person = dict()

        parsed_person['id'] = person['id']
        parsed_person['first_name'] = person['force_first_name']
        parsed_person['last_name'] = person['last_name']
        parsed_person['gender'] = person['details'].get('757881885', {}).get('name')
        parsed_person['age'] = _age(person['details'].get('birthdate'))
        parsed_person['campus'] = person['details'].get('1847408178', {}).get('name')
        parsed_person['mobile'] = _mobile(person['details'].get('79910291', []))
        parsed_person['email'] = _email(person['details'].get('1676694648', []))
        parsed_person['tags'] = []

        return parsed_person

    @classmethod
    def _get_tags(cls):
        result = cls.get('tags/list_tags')
        if result.status_code != 200:
            return None

        return json.loads(result.content)

    @classmethod
    def _get_people(cls, detail=False, attempt=1):
        detail_flag = 0
        if detail:
            detail_flag = 1

        result = cls.get(f'people/?details={detail_flag}')
        if result.status_code != 200:
            raise Exception('Retrieving tags unsuccessful!')

        if result.content:
            return json.loads(result.content)
        else:
            if attempt < 2:
                return cls._get_people(detail=detail, attempt=2)
            else:
                return []

    @classmethod
    def _get_users_by_tag_id(cls, tag_id):
        if not tag_id:
            raise Exception(f"Invalid value for tag_id: {tag_id}")

        filter_json = json.dumps({'tag_contains': f'y_{tag_id}'})
        result = cls.get(f'people/?filter_json={filter_json}')
        if result.status_code != 200:
            raise Exception('Retrieving tags unsuccessful!')

        if result.content:
            return json.loads(result.content)
        else:
            return []
