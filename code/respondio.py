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

    @classmethod
    def set_dry_run(cls, dry_run):
        cls.dry_run = dry_run

    @classmethod
    def sync_to_respondio(cls, breeze_contacts: []):
        print('Syncing to RespondIO...')
        try:
            respondio_contacts_data, _metadata = cls.get_contacts()

            creates, updates, deletes = compare_contacts(
                breeze_contacts=breeze_contacts,
                respondio_contacts=respondio_contacts_data
            )

            if cls.dry_run:
                output_dry_run_results(creates=creates, updates=updates, deletes=deletes)

            # Handle remote creates
            failed_creates = cls.create_remote_contacts(creates)

            # Handle remote updates
            failed_updates = cls.update_remote_contacts(updates)

            # Handle remote deletes
            failed_deletes = []
            if not FILTERED_EXPORT_ENABLED:
                # A remote delete is not permitted if a filtered export is being done,
                # because there's no way of knowing who should not exist on repond.io
                # with an incomplete list
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
    def get_contacts(cls):
        resource = f'contact/by_custom_field?name={GET_BY_REMOTE_FIELD_NAME}&value={GET_BY_REMOTE_FIELD_VALUE}'
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
                response = cls.post(f'contact/{new_contact_id}/tags', {'tags': tags})

                if response.status_code != 200:
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

        for contact_to_update in updates:
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

                if tags_to_add:
                    tags_payload = {
                        'tags': tags_to_add
                    }
                    response = cls.post(f"contact/{contact_id}/tags", tags_payload)
                    if response.status_code != 200:
                        failed_updates.append(cls._failed_response(contact_to_update, response))
                        continue

                if tags_to_remove:
                    tags_payload = {
                        'tags': tags_to_remove
                    }
                    response = cls.delete(f"contact/{contact_id}/tags", tags_payload)
                    if response.status_code != 200:
                        failed_updates.append(cls._failed_response(contact_to_update, response))
                        continue

        return failed_updates

    @classmethod
    def delete_remote_contacts(cls, contacts_to_delete):
        # Update each contact's custom_field.active to false
        delete_updates = []
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
