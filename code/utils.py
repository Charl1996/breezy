from code.configs import API_FIELD_MAPPINGS


def map_to_respondio_api_fields(breeze_contacts):
    mapped_contacts = []

    for contact_data in breeze_contacts:
        mapped_contact = {}
        for breeze_header, api_field in API_FIELD_MAPPINGS.items():
            if api_field['field_id'] == 'tags':
                # Tags is a special case
                tags_string = contact_data[breeze_header]
                tags_list = tags_string.split(',') if tags_string else []
                if any(tags_list):
                    tags_list = [tag.strip() for tag in tags_list]

                mapped_contact[api_field['field_id']] = tags_list
            else:
                mapped_contact[api_field['field_id']] = str(contact_data[breeze_header]) if contact_data[breeze_header] else ''
        mapped_contacts.append(mapped_contact)

    return mapped_contacts


def determine_updates(matched_contacts):
    updates = []

    for contacts_match in matched_contacts:
        cms_contact = contacts_match['breeze']
        remote_contact = contacts_match['respondio']

        custom_fields_to_update = {}
        tags_to_update = []
        # Compare key-value pairs
        for key in cms_contact.keys():
            if key == 'tags':
                cms_contact_tags = set(cms_contact.get(key, []))
                remote_tags = set(remote_contact.get(key, []))

                tags_to_add = cms_contact_tags.difference(remote_tags)
                tags_to_remove = remote_tags.difference(cms_contact_tags)

                if tags_to_add or tags_to_remove:
                    tags_to_update.append({
                        'add': tags_to_add,
                        'remove': tags_to_remove,
                    })
            else:
                cms_contact_value = cms_contact.get(key, '')
                remote_value = remote_contact['custom_fields'].get(key, '')

                if cms_contact_value != remote_value:
                    custom_fields_to_update = {key: cms_contact_value, **custom_fields_to_update}

        if custom_fields_to_update:
            remote_contact['custom_fields'] = custom_fields_to_update
        else:
            remote_contact.pop('custom_fields')

        if tags_to_update:
            remote_contact['tags'] = tags_to_update
        else:
            remote_contact.pop('tags')

        # Add the breeze_id to remote_contact for auditing purposes
        remote_contact['breeze_id'] = cms_contact['breeze_id']

        if custom_fields_to_update or tags_to_update:
            updates.append(remote_contact)

    return updates


def compare_contacts(breeze_contacts=[], respondio_contacts=[]):
    """
        This functions does the heavy-lifting of the remote syncing algorithm
    """

    def _parse_delete_contact(contact):
        return {'id': contact.get('id'), 'breeze_id': contact['custom_fields']['breeze_id']}

    new_contacts = []
    matched_contacts = []

    # As the loop iterates, the matching contacts' id's will be removed so that only those
    # that did not match remains
    potential_contacts_to_delete = [
        _parse_delete_contact(rc)
        for rc in respondio_contacts
        if 'breeze_id' in rc.get('custom_fields', {}).keys()
    ]

    for breeze_contact in map_to_respondio_api_fields(breeze_contacts):
        breeze_id = breeze_contact['breeze_id']

        matched_responseio_contact = None
        for respond_contact in respondio_contacts:
            custom_fields = respond_contact['custom_fields']

            if 'breeze_id' in custom_fields.keys():
                # Handle CMS contact
                if custom_fields['breeze_id'] == breeze_id:
                    # Contact match, so this contact should be removed from potential_contacts_to_delete list
                    matched_responseio_contact = respond_contact

                    # Remove from delete list
                    item_to_remove = _parse_delete_contact(respond_contact)
                    potential_contacts_to_delete.remove(item_to_remove)
                    break

        if matched_responseio_contact:
            matched_contacts.append({
                'breeze': breeze_contact,
                'respondio': matched_responseio_contact,
            })
        else:
            new_contacts.append(breeze_contact)

    creates = new_contacts
    updates = determine_updates(matched_contacts)
    deletes = potential_contacts_to_delete

    return creates, updates, deletes


def _print_creates(data):
    print('CREATES')
    for contact in data:
        output_string = ""
        for field_name, field_value in contact.items():
            if not output_string:
                output_string = f'{str(field_name)}={str(field_value)}'
            else:
                output_string = output_string + ', ' + f'{str(field_name)}={str(field_value)}'
        print(output_string)
    print('----------' + '\n')


def _print_updates(data):
    print('UPDATES')
    for contact in data:
        output_string = ""
        for field_name, field_value in contact.items():
            if not output_string:
                output_string = f'{str(field_name)}={str(field_value)}'
            else:
                output_string = output_string + ', ' + f'{str(field_name)}={str(field_value)}'
        print(output_string)
    print('----------' + '\n')


def _print_deletes(data):
    print('DELETES')
    output_string = ''
    for item in data:
        if not output_string:
            output_string = item
        else:
            output_string = f'{output_string}, {item}'
    print(output_string)
    print('----------' + '\n')


def output_dry_run_results(creates=[], updates=[], deletes=[]):
    print(' ------- DRY RUN OUTPUT -------')
    _print_creates(creates)
    _print_updates(updates)
    _print_deletes(deletes)
    # Exit prematurely, since no additional work is needed
    exit(0)
