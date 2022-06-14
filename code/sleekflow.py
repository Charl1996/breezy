import requests
import json
from configs import (
    SLEEKFLOW_API_KEY,
    SLEEKFLOW_API_URL,
    FILTERED_EXPORT_ENABLED,
    GET_BY_REMOTE_FIELD_NAME,
    GET_BY_REMOTE_FIELD_VALUE,
)
from utils import compare_contacts, output_dry_run_results
from logger import log


def _get_stat(planned, failed):
    return f'{len(failed)}/{len(planned)}'


class SleekflowRequests:

    base_url = SLEEKFLOW_API_URL

    @classmethod
    def headers(cls):
        return {
            'Content-Type': 'application/json',
        }

    @classmethod
    def ensure_no_beginning_slash(cls, string):
        if string.startswith('/'):
            return string[1:]
        else:
            return string

    @classmethod
    def get(cls, resource):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=cls.base_url,
            resource_endpoint=cls.ensure_no_beginning_slash(resource)
        )
        return requests.get(url, headers=cls.headers())

    @classmethod
    def put(cls, resource, data):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=cls.base_url,
            resource_endpoint=cls.ensure_no_beginning_slash(resource)
        )
        return requests.put(url, data=json.dumps(data), headers=cls.headers())

    @classmethod
    def post(cls, resource, data):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=cls.base_url,
            resource_endpoint=cls.ensure_no_beginning_slash(resource)
        )
        return requests.post(url, data=json.dumps(data), headers=cls.headers())

    @classmethod
    def delete(cls, resource, data):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=cls.base_url,
            resource_endpoint=cls.ensure_no_beginning_slash(resource)
        )
        return requests.delete(url, data=json.dumps(data), headers=cls.headers())

    @classmethod
    def add_api_key(cls, resource):
        if "?" in resource:
            return f"{resource}&apikey={SLEEKFLOW_API_KEY}"
        return "{resource}?apikey={api_key}".format(
            resource=resource,
            api_key=SLEEKFLOW_API_KEY
        )


class Sleekflow(SleekflowRequests):
    dry_run = False

    FAILED = 'failed'
    SUCCESS = 'success'

    LOGGER_ID = 'Sleekflow'
    MAX_API_CONTACTS = 1000

    @classmethod
    def set_dry_run(cls, dry_run):
        cls.dry_run = dry_run

    @classmethod
    def sync(cls, breeze_contacts: []):
        print('Syncing...')

        # sleekflow_contacts = cls.get_all_contacts()

        cls.create_contacts(breeze_contacts)

        # creates, updates, deletes = compare_contacts(
        #     breeze_contacts=breeze_contacts,
        #     sleekflow_contacts=sleekflow_contacts
        # )

        # failed_creates = cls.create_contacts(creates)
        # failed_updates = cls.update_contacts(updates)
        #
        # if not FILTERED_EXPORT_ENABLED:
        #     # A remote delete is not permitted if a filtered export is being done,
        #     # because there's no way of knowing who should not exist on repond.io
        #     # with an incomplete list
        #     log(f'{cls.LOGGER_ID} sync_to_respondio: handling "delete" contacts')
        #     failed_deletes = cls.cls.delete_contacts(deletes)

        return {
            'status': cls.SUCCESS,
            'failed': {},
            'stats': {
                'creates': len(breeze_contacts),
                'updates': 0,
                'deletes': 0,
            },
        }

    @classmethod
    def get_all_contacts(cls):
        all_contacts_fetched = False
        all_contacts = []
        offset = 0

        while not all_contacts_fetched:
            new_contacts = cls.get_contacts(offset=offset)
            all_contacts = all_contacts + new_contacts

            if len(new_contacts) < cls.MAX_API_CONTACTS:
                all_contacts_fetched = True
            else:
                offset += cls.MAX_API_CONTACTS

        return all_contacts

    @classmethod
    def get_contacts(cls, offset):
        resource_url = f'/contact?offset={offset}'
        authenticated_resource_url = cls.add_api_key(resource_url)

        result = cls.get(authenticated_resource_url)
        if result.status_code == 200:
            return json.loads(result.content)
        else:
            raise Exception('get_contacts failed - I quit!')

    @classmethod
    def create_contacts(cls, contacts):
        # Todo:
        # Add birth date
        # Add age

        print('Handling labels...')
        # Get all labels
        res = cls.get(cls.add_api_key('labels'))

        labels = json.loads(res.content)
        data = [{'id': label['id'] for label in labels}]
        # Delete all labels
        res = cls.delete(cls.add_api_key('labels'), data=data)

        print('Parsing contacts...')
        data = []

        for contact in contacts:
            if contact.get('Phone Number'):
                new_contact = {
                    'firstName': contact['First Name'],
                    'lastName': contact['Last Name'],
                    'addLabels': contact['Tags'].split(', '),
                    'labels': contact['Tags'].split(', '),
                    'email': contact.get('Email'),
                    'phoneNumber': contact.get('Phone Number'),
                }
                data.append(new_contact)

        print('Making the request...')
        endpoint = cls.add_api_key('Contact/AddOrUpdate')
        res = cls.post(endpoint, data)

        print(res.status_code)


    @classmethod
    def update_contacts(cls, contacts):
        pass

    @classmethod
    def delete_contacts(cls, contacts):
        pass
