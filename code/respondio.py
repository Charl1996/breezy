import requests
import json
from configs import (
    RESPONDIO_API_URL,
    RESPONDIO_API_TOKEN,
    FILTERED_EXPORT_ENABLED,
    GET_BY_REMOTE_FIELD_NAME,
    GET_BY_REMOTE_FIELD_VALUE,
)
from utils import compare_contacts, output_dry_run_results
from logger import log


def _get_stat(planned, failed):
    return f'{len(failed)}/{len(planned)}'


class RespondIORequests:

    @classmethod
    def headers(cls):
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {RESPONDIO_API_TOKEN}'
        }

    @classmethod
    def get(cls, resource):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=RESPONDIO_API_URL,
            resource_endpoint=resource
        )
        return requests.get(url, headers=cls.headers())

    @classmethod
    def put(cls, resource, data):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=RESPONDIO_API_URL,
            resource_endpoint=resource
        )
        return requests.put(url, data=json.dumps(data), headers=cls.headers())

    @classmethod
    def post(cls, resource, data):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=RESPONDIO_API_URL,
            resource_endpoint=resource
        )
        return requests.post(url, data=json.dumps(data), headers=cls.headers())

    @classmethod
    def delete(cls, resource, data):
        url = '{base_url}{resource_endpoint}'.format(
            base_url=RESPONDIO_API_URL,
            resource_endpoint=resource
        )
        return requests.delete(url, data=json.dumps(data), headers=cls.headers())


class RespondIO(RespondIORequests):
    dry_run = False

    FAILED = 'failed'
    SUCCESS = 'success'

    MAX_UPDATEABLE_TAGS = 10
    LOGGER_ID = 'RespondIO'

    @classmethod
    def set_dry_run(cls, dry_run):
        cls.dry_run = dry_run

    @classmethod
    def sync_to_respondio(cls, breeze_contacts: []):
        print('sync_to_respondio...')
        try:
            current_query_page = 1
            respondio_contacts_data = []

            log(f'{cls.LOGGER_ID} sync_to_respondio: retrieving contacts')
            while True:
                log(f'{cls.LOGGER_ID} sync_to_respondio: retrieving page data: {current_query_page}')
                contacts_data, _metadata = cls.get_contacts(current_query_page)
                if not any(contacts_data):
                    break
                respondio_contacts_data.extend(contacts_data)
                current_query_page += 1

            log(f'{cls.LOGGER_ID} sync_to_respondio: comparing contacts')
            creates, updates, deletes = compare_contacts(
                breeze_contacts=breeze_contacts,
                respondio_contacts=respondio_contacts_data
            )

            if cls.dry_run:
                output_dry_run_results(creates=creates, updates=updates, deletes=deletes)

            # Handle remote creates
            log(f'{cls.LOGGER_ID} sync_to_respondio: handling "create" contacts')
            failed_creates = cls.create_remote_contacts(creates)

            # Handle remote updates
            log(f'{cls.LOGGER_ID} sync_to_respondio: handling "update" contacts')
            failed_updates = cls.update_remote_contacts(updates)

            # Handle remote deletes
            failed_deletes = []
            if not FILTERED_EXPORT_ENABLED:
                # A remote delete is not permitted if a filtered export is being done,
                # because there's no way of knowing who should not exist on repond.io
                # with an incomplete list
                log(f'{cls.LOGGER_ID} sync_to_respondio: handling "delete" contacts')
                failed_deletes = cls.delete_remote_contacts(deletes)

            return {
                'status': cls.FAILED if any(failed_creates) or any(failed_updates) or any(
                    failed_deletes) else cls.SUCCESS,
                'failed': {
                    'creates': failed_creates,
                    'updates': failed_updates,
                    'deletes': failed_deletes,
                },
                'stats': {
                    'creates': _get_stat(
                        creates,
                        failed_creates['contact_creates'] + failed_creates['contacts_ignored'],
                    ),
                    'updates': _get_stat(
                        updates,
                        failed_updates + failed_creates['tags_updates'],
                    ),
                    'deletes': _get_stat(deletes, failed_deletes),
                },
            }
        except Exception as e:
            print(f'sync_to_respondio failed')
            raise e

    @classmethod
    def get_contacts(cls, page):
        resource = f'contact/by_custom_field?name={GET_BY_REMOTE_FIELD_NAME}&value={GET_BY_REMOTE_FIELD_VALUE}&page={page}'
        response = cls.get(resource)

        if response.status_code == 200:
            content = json.loads(response.content)
            return content.get('data'), content.get('meta')
        else:
            raise Exception("get_contacts failed - I'm quitting!")

    @classmethod
    def create_remote_contacts(cls, creates):
        failed_creates = []
        failed_tag_updates = []
        ignored_creates = []

        print('Creating contacts...')
        for contact_to_create in creates:
            if not contact_to_create['phone']:
                ignored_creates.append(
                    cls._failed_response(
                        contact_to_create, None, message='No phone number!')
                )
                continue

            tags = None
            if 'tags' in contact_to_create:
                tags = contact_to_create.pop('tags')

            payload = cls.parse_to_respondio_payload(custom_fields_data=contact_to_create)
            response = cls.post('contact/', payload)

            if response.status_code != 200:
                failed_creates.append(cls._failed_response(contact_to_create, response))
                continue

            new_contact_data = json.loads(response.content).get('data', {})
            new_contact_id = new_contact_data.get('id')

            if new_contact_id and tags:
                success, response = cls._update_tags('add', new_contact_id, tags)

                if not success:
                    failed_tag_updates.append(cls._failed_response(contact_to_create, response))
                    continue

        return {
            'contact_creates': failed_creates,
            'tags_updates': failed_tag_updates,
            'contacts_ignored': ignored_creates,
        }

    @classmethod
    def update_remote_contacts(cls, updates):
        """
            'updates' format:
            {
                'id': <id>,
                'custom_fields': {                  --- optional
                    <field_name>: <field_value>,
                    <field_name>: <field_value>,
                },
                tags: [<tag>, <tag>, ...],        --- optional
            }
        """
        failed_updates = []
        print('Updating contacts...')
        for contact_to_update in updates:
            if 'phone' in contact_to_update.get('custom_fields', {}).keys() and not contact_to_update['custom_fields']['phone']:
                failed_updates.append(
                    cls._failed_response(
                        contact_to_update, None, message='Invalid phone number!')
                )
                contact_to_update['custom_fields'].pop('phone')

            contact_id = contact_to_update['id']

            if contact_to_update.get('custom_fields'):
                parsed_custom_fields_data = cls.parse_to_respondio_payload(
                    custom_fields_data=contact_to_update['custom_fields']
                )
                response = cls.put(f"contact/{contact_id}", parsed_custom_fields_data)

                if response.status_code != 200:
                    failed_updates.append(cls._failed_response(contact_to_update, response))
                    continue

            # Tags updates must be handled separately
            if contact_to_update.get('tags'):
                tags_to_add = []
                tags_to_remove = []

                for tag in contact_to_update['tags']:
                    tags_to_add.extend(tag.get('add', []))
                    tags_to_remove.extend(tag.get('remove', []))

                success, response = cls._update_tags('add', contact_id, tags_to_add)
                if not success:
                    failed_updates.append(cls._failed_response(contact_to_update, response))
                    continue

                success, response = cls._update_tags('remove', contact_id, tags_to_remove)
                if not success:
                    failed_updates.append(cls._failed_response(contact_to_update, response))
                    continue

        return failed_updates

    @classmethod
    def delete_remote_contacts(cls, contacts_to_delete):
        # Update each contact's custom_field.active to false
        delete_updates = []
        print('Deleting contacts...')
        for delete_contact in contacts_to_delete:
            delete_updates.append({
                'id': delete_contact['id'],
                'custom_fields': {'active': 'false'},
                'breeze_id': delete_contact['breeze_id'],
            })

        return cls.update_remote_contacts(delete_updates)

    @classmethod
    def parse_to_respondio_payload(cls, custom_fields_data=None, contact_id=None, tags=None):
        """
            'custom_field' format:
            {
                <field_name >: <field_value>,
                <field_name >: <field_value>,
                ...
            }

            'tags' format:
            [<tag>, <tag>, ...]
        """
        parsed_data = {}

        if custom_fields_data:
            custom_fields_list = []
            for field_name, field_value in custom_fields_data.items():
                custom_fields_list.append({
                    'name': field_name,
                    'value': field_value
                })
            parsed_data = {'custom_fields': custom_fields_list}

        if contact_id:
            parsed_data['id'] = contact_id

        if tags:
            parsed_data['tags'] = tags

        return parsed_data

    @classmethod
    def _failed_response(cls, contact, response, message=None):
        failed_response = {'contact': contact}
        if message:
            return {
                'error': {
                    'reason': message,
                }, **failed_response
            }
        elif response.status_code:
            return {
                'error': {
                    'status_code': str(response.status_code),
                    'reason': json.loads(response.content),
                }, **failed_response
            }
        else:
            return {
                'error': {
                    'reason': 'Something went wrong'
                }
            }

    @classmethod
    def _update_tags(cls, method, contact_id, tags):
        if not tags:
            return True, None

        url = f"contact/{contact_id}/tags"
        tags_to_update = [tags]

        if len(tags) > cls.MAX_UPDATEABLE_TAGS:
            # Divide list of tags into groups of size MAX_UPDATEABLE_TAGS
            tags_to_update = [
                tags[i:i + cls.MAX_UPDATEABLE_TAGS]
                for i in range(0, len(tags), cls.MAX_UPDATEABLE_TAGS)
            ]

        for tags_partition in tags_to_update:
            if method == 'add':
                response = cls.post(url, {'tags': tags_partition})
            else:
                response = cls.delete(url, {'tags': tags_partition})

            if response.status_code != 200:
                return False, response

        return True, None
