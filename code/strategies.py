import pandas as pd
import re
import os

from datetime import datetime
from configs import (
    HEADER_VALUE_MAPPINGS,
    DATA_OUTPUT_FILE_NAME,
    INPUT_COLUMNS_CLEANING_FUNCTIONS,
    OUTPUT_COLUMNS_CLEANING_FUNCTIONS,
    DYNAMIC_TAGS_CRITERIA,
    FILTERED_EXPORT_ENABLED,
    EXPORT_CONTACTS_WHERE_COLUMNS_HAS_VALUE,
    FAILED_SYNC_DATAFRAME_OUTPUT_FILE_NAME,
    BREEZE_TO_CSV_HEADER_CONVERTERS,
)
from respondio import RespondIO
from breeze import Breeze
from utils import send_email
from logger import log

NUMERIC_OPERATORS = ['<', '<=', '>', '>=', '%']


class DataCleaner:

    @classmethod
    def clean_phone_number(cls, phone_number):
        # Replace odd characters
        stripped_number = re.sub(r'[ +()-]', '', phone_number)

        if stripped_number.startswith('27') and len(stripped_number) == 11:
            return True, stripped_number
        if stripped_number.startswith('0') and len(stripped_number) == 10:
            return True, f'27{stripped_number[1:]}'

        # Return original for inspection
        return False, phone_number

    @classmethod
    def clean_tags(cls, tag):
        tag = tag.replace('(', '- ')
        tag = tag.replace(')', '')
        return True, tag


class BaseStrategy(DataCleaner):

    @classmethod
    def execute(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def get_data(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def clean_data(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def report_faulty_data(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def handle_cleaned_data(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def notify_results(cls, *args, **kwargs):
        raise NotImplementedError

    @classmethod
    def dynamic_tags(cls, dataframe, data_index):
        tags = []

        for tag_name, tag_criteria in DYNAMIC_TAGS_CRITERIA.items():
            # Extract criteria logic from string
            column, operator, value = re.split(r'`*`', tag_criteria)[1:-1]
            operator = operator.strip()

            variable_value = dataframe[column][data_index]
            reference_value = value

            if variable_value and str(variable_value) == 'nan':
                continue

            # Basic check to see if values needs to be parsed to integer for eval
            if operator in NUMERIC_OPERATORS:
                variable_value = int(variable_value)
                reference_value = int(reference_value)

            if operator == '=':
                operator = '=='

            if eval(f'variable_value {operator} reference_value'):
                tags.append(tag_name)

        return tags


class CSVHandler:
    export_dir = None

    @classmethod
    def export_to_csv(cls, dataframe, output_path=None, generated_input_file=False):
        if generated_input_file:
            export_path = output_path
        else:
            if not cls.export_dir:
                import datetime

                timestamp = datetime.datetime.now()
                export_timestamp = '{year}_{month}_{day}_{hour}:{minute}:{second}'.format(
                    year=timestamp.year,
                    month=timestamp.month,
                    day=timestamp.day,
                    hour=timestamp.hour,
                    minute=timestamp.minute,
                    second=timestamp.second,
                )
                cls.export_dir = f'sync_{export_timestamp}'
                os.mkdir(f'data_files/output/{cls.export_dir}')

            path = DATA_OUTPUT_FILE_NAME
            if output_path:
                path = output_path

            export_path = f'data_files/output/{cls.export_dir}/{path}'
        dataframe.to_csv(export_path, index=False)
        return export_path

    @classmethod
    def get_header(cls, dataframe):
        return dataframe.columns.values.tolist()

    @classmethod
    def get_csv_dataframe(cls, file_path):
        return pd.read_csv(file_path)


class CSVStrategy(BaseStrategy, CSVHandler):

    @classmethod
    def get_sample_file_headers(cls, path):
        return cls.get_header(cls.get_csv_dataframe(path))

    @classmethod
    def get_data(cls, samplefile, datafile):
        respondio_headers = cls.get_sample_file_headers(samplefile)
        people_data = cls.get_csv_dataframe(datafile)
        return respondio_headers, people_data

    @classmethod
    def clean_data(cls, dataframe, dataframe_cleaning_functions):
        headers = cls.get_header(dataframe)
        faulty_data = {}

        for header in headers:
            if header in dataframe_cleaning_functions.keys():
                cleaned_data, faulty_data_values = cls.clean_column(
                    dataframe[header].values.tolist(),
                    dataframe_cleaning_functions[header]
                )
                dataframe[header] = cleaned_data

                if faulty_data_values:
                    faulty_data[header] = faulty_data_values
        return dataframe, faulty_data

    @classmethod
    def clean_column(cls, column: [], cleaning_function: str):
        cleaned_rows = []
        faulty_rows = []

        for row_item in column:
            if not row_item or str(row_item) == 'nan':
                cleaned_rows.append('')
                continue

            is_valid, cleaned_row_item = eval(f'cls.{cleaning_function}(row_item)')
            if is_valid:
                cleaned_rows.append(cleaned_row_item)
            else:
                cleaned_rows.append('')
                faulty_rows.append(cleaned_row_item)

        return cleaned_rows, faulty_rows

    @classmethod
    def parse_to_new_dataframe(cls, new_dataframe_headers, old_dataframe):
        parsed_header_data = {}

        for header in new_dataframe_headers:
            new_column_data = []
            default_column_cell_value = ''

            # Determine what header will be used for the new dataframe
            if header in HEADER_VALUE_MAPPINGS.keys():
                # Get the mapped header value
                breeze_headers = HEADER_VALUE_MAPPINGS[header].get('breeze_headers', [])
                lambda_function = HEADER_VALUE_MAPPINGS[header].get('lambda')
                default_column_cell_value = HEADER_VALUE_MAPPINGS[header].get('default')
            else:
                # Headers are the same
                breeze_headers = [header]
                lambda_function = ''

            # Loop through existing dataframe and consolidate data to match new headers
            for data_index in range(len(old_dataframe)):
                cell_data = []

                # Go through every specified Breeze header to be merged into this one cell
                for _header in breeze_headers:
                    if _header.startswith('*'):
                        postfix = _header[1:]

                        for old_header in cls.get_header(old_dataframe):
                            if old_header.endswith(postfix):
                                if old_dataframe[old_header][data_index] == 'x':
                                    tag = old_header[:old_header.find("(Tag)")].strip()
                                    cell_data.append(tag)
                    else:
                        breeze_cell_data = old_dataframe[_header][data_index]
                        if not breeze_cell_data or str(breeze_cell_data) == 'nan':
                            continue
                        cell_data.append(breeze_cell_data)

                # Handle additional calculated data for specific cell specified by the
                # 'lambda' function in the HEADER_VALUE_MAPPINGS config
                if lambda_function:
                    cell_data.extend(eval(f"cls.{lambda_function}(old_dataframe, data_index)"))

                if not cell_data:
                    new_column_data.append(default_column_cell_value)  # Empty cell
                elif len(cell_data) == 1:
                    new_column_data.append(cell_data[0])
                else:
                    # If multiple items merged together, separate by comma
                    new_column_data.append(', '.join(cell_data))

            parsed_header_data[header] = new_column_data

        new_dataframe = pd.DataFrame(data=parsed_header_data)

        if FILTERED_EXPORT_ENABLED:
            new_dataframe = cls.filter_dataframe_by_columns_values(new_dataframe)

        return new_dataframe

    @classmethod
    def filter_dataframe_by_columns_values(cls, dataframe):
        def _matches(contacts_tags, exportable_tags):
            export_match_list = []
            for tags in contacts_tags:
                # Skip iteration if no data present
                if not tags or tags is None:
                    export_match_list.append(False)
                    continue

                contains_all_tags = True
                for tag in exportable_tags:
                    if tag not in tags:
                        contains_all_tags = False
                        break

                export_match_list.append(contains_all_tags)
            return export_match_list

        matches = None
        for col, values in EXPORT_CONTACTS_WHERE_COLUMNS_HAS_VALUE.items():
            if matches is None:
                matches = _matches(dataframe[col], values)
            else:
                matches = matches and _matches(dataframe[col], values)

        return dataframe.loc[matches]


class StrategyOne(CSVStrategy):

    @classmethod
    def execute(cls, samplefile, datafile=None, *args, **kwargs):
        if datafile is None:
            return 'No datafile found!'
        try:
            print('Getting data...')
            respondio_headers, people_dataframe = cls.get_data(samplefile, datafile)

            print('Cleaning pre-processed data...')
            cleaned_data, faulty_input_data = cls.clean_data(people_dataframe, INPUT_COLUMNS_CLEANING_FUNCTIONS)

            if faulty_input_data:
                cls.report_faulty_data(faulty_input_data)

            new_dataframe = cls.parse_to_new_dataframe(respondio_headers, cleaned_data)

            print('Cleaning post-processed data...')
            post_processed_cleaned_data, _faulty_data = cls.clean_data(new_dataframe, OUTPUT_COLUMNS_CLEANING_FUNCTIONS)

            cls.handle_cleaned_data(post_processed_cleaned_data)
        except Exception as e:
            raise e
        return None

    @classmethod
    def report_faulty_data(cls, faulty_data):
        print('')
        print("The following columns contains faulty data:")
        for k, v in faulty_data.items():
            print(f'{k}: {v}')
        print('')

    @classmethod
    def handle_cleaned_data(cls, new_dataframe):
        print('Exporting to .csv...')
        cls.export_to_csv(new_dataframe)

    @classmethod
    def notify_results(cls, error=None):
        print('')
        if error is None:
            print('All done!')
        else:
            print('Something went wrong!')
            print(error)


class StrategyTwo(StrategyOne):
    export = False
    processed_dataframe = None
    remote_sync_result = {}

    @classmethod
    def execute(cls, samplefile, datafile, *args, **kwargs):
        RespondIO.set_dry_run(kwargs['dry_run'])

        cls.export = kwargs.get('export')
        super().execute(samplefile, datafile)

    @classmethod
    def report_faulty_data(cls, faulty_data):
        super().report_faulty_data(faulty_data)

    @classmethod
    def parse_to_dictionary(cls, dataframe):
        def _parse_contact(columns, i):
            return {c: dataframe[c][i] for c in columns}

        dict_data = []
        keys = cls.get_header(dataframe)

        for index in dataframe.index:
            dict_data.append(_parse_contact(keys, index))

        return dict_data

    @classmethod
    def handle_cleaned_data(cls, dataframe):
        cls.processed_dataframe = dataframe

        if cls.export:
            super().handle_cleaned_data(cls.processed_dataframe)

        # Push to api
        contacts = cls.parse_to_dictionary(cls.processed_dataframe)
        cls.remote_sync_result = RespondIO.sync_to_respondio(contacts)

        if cls.remote_sync_result.get('status') == RespondIO.FAILED and cls.export:
            cls._export_failed_sync_contacts()

    @classmethod
    def notify_results(cls, *args, **kwargs):
        if not cls.export:
            print('\n')
            if cls.remote_sync_result.get('status') == RespondIO.FAILED:
                failed_syncs = cls.remote_sync_result.get('failed')

                if failed_syncs:
                    print('------- FAILURES DURING CREATES -------')
                    if failed_syncs['creates']['contacts_ignored']:
                        print('IGNORED CONTACTS')
                        for ic in failed_syncs['creates']['contacts_ignored']:
                            print(f"Contact: {ic['contact']}, error: {ic['error']}")

                    if failed_syncs['creates']['contact_creates']:
                        print('FAILED CONTACT CREATES')
                        for _fc in failed_syncs['creates']['contact_creates']:
                            print(f"Contact: {_fc['contact']}, error: {_fc['error']}")

                    if failed_syncs['creates']['tags_updates']:
                        print('FAILED TAGS ASSIGNMENTS')
                        for tu in failed_syncs['creates']['tags_updates']:
                            print(f"Contact: {tu['contact']}, error: {tu['error']}")

                    print('------- FAILURES DURING UPDATES -------')
                    for fc in failed_syncs['updates']:
                        print(f"Contact: {fc['contact']}, error: {fc['error']}")

                    print('------- FAILURES DURING DELETES -------')
                    for fc in failed_syncs['deletes']:
                        print(f"Contact: {fc['contact']}, error: {fc['error']}")

        stats = cls.remote_sync_result['stats']
        print('')
        print(f"{stats['creates']} creates failed")
        print(f"{stats['updates']} updates failed")
        print(f"{stats['deletes']} deletions failed")

    @classmethod
    def _export_failed_sync_contacts(cls):
        dataframe = cls.processed_dataframe
        # This setting only suppresses an irrelevant warning message
        pd.options.mode.chained_assignment = None

        def _get_subframe(contacts_list, action=''):
            breeze_ids = []
            errors = []
            status_codes = []

            for c in contacts_list:
                contact = c['contact']
                error = c['error']

                breeze_ids.append(int(contact['breeze_id']))  # Need to cast back to int
                errors.append(error.get('reason'))
                status_codes.append(error.get('status_code', ''))

            subframe = dataframe[dataframe['custom_field.breeze_id'].isin(breeze_ids)]

            # DELETE needs to be handled separately because the subframe will be empty
            # due to the contact not being in the dataframe.
            if action == 'DELETE':
                # Populate the custom_field.breeze_id so contact can be traced on respond.io
                subframe['custom_field.breeze_id'] = breeze_ids
            subframe['Request Method'] = action
            subframe['Error'] = errors
            subframe['Request status code'] = status_codes

            return subframe

        failed_syncs = cls.remote_sync_result.get('failed')
        subframes = []

        ignored = failed_syncs['creates']['contacts_ignored']
        subframes.append(_get_subframe(ignored, action='CREATE'))

        failed_created = failed_syncs['creates']['contact_creates']
        subframes.append(_get_subframe(failed_created, action='CREATE'))

        failed_deleted = failed_syncs['deletes']
        subframes.append(_get_subframe(failed_deleted, action='DELETE'))

        failed_tags_updates = failed_syncs['creates']['tags_updates']
        failed_updates = failed_syncs['updates'] + failed_tags_updates
        subframes.append(_get_subframe(failed_updates, action='UPDATE'))

        new_dataframe = pd.concat(subframes)
        if len(new_dataframe.index) > 0:
            print('Exporting sync failures...')
            output_path = cls.export_to_csv(new_dataframe, output_path=FAILED_SYNC_DATAFRAME_OUTPUT_FILE_NAME)
            return output_path


class StrategyThree(StrategyTwo):
    faulty_data = None

    @classmethod
    def execute(cls, samplefile, datafile, *args, **kwargs):
        log('Executing Strategy 3')
        success, contacts, tags = Breeze.get_contacts()

        if success:
            dataframe = cls.parse_to_dataframe(contacts, tags)
            cls.export_to_csv(dataframe, datafile, generated_input_file=True)

            super().execute(samplefile, datafile, *args, **kwargs)
        else:
            log('Failed to retrieve Breeze contacts. Notifying via email')
            cls.send_email(
                'Failed sync',
                'Could not retrieve Breeze contacts'
            )
            return None

    @classmethod
    def report_faulty_data(cls, _faulty_data):
        pass

    @classmethod
    def handle_cleaned_data(cls, dataframe):
        super().handle_cleaned_data(dataframe)

    @classmethod
    def notify_results(cls, *args, **kwargs):
        today_date = datetime.strftime(datetime.today(), "%d-%m-%Y %H:%M:%S")
        attachment = None

        if cls.remote_sync_result.get('status') == RespondIO.FAILED:
            subject = f'Some items failed to sync - {today_date}'
            attachment_file_path = cls._get_failed_results_attachment_path()

            stats = cls.remote_sync_result['stats']

            email_body = f"""
            Creates failed: {stats['creates']}
            Updates failed: {stats['updates']}
            Deletes failed: {stats['deletes']}
            
            See the attached document for the failed results.
            """
        else:
            subject = f'Successful sync - {today_date}'
            email_body = f"""
            Your data has been successfully synced! 
            """

        attachment_info = {
            'path': attachment_file_path,
            'name': 'failed_syncs.csv'
        }
        send_email(subject, email_body, attachment_info=attachment_info)

    @classmethod
    def parse_to_dataframe(cls, raw_breeze_contacts, tags):
        dataframe_dict = dict()
        # Initialise empty header columns
        for _x, csv_header in BREEZE_TO_CSV_HEADER_CONVERTERS.items():
            dataframe_dict[csv_header] = []

        for tag in tags:
            qualified_header = f'{tag} (Tag)'
            dataframe_dict[qualified_header] = [None for i in range(len(raw_breeze_contacts))]

        for index, contact in enumerate(raw_breeze_contacts):
            for breeze_header, csv_header in BREEZE_TO_CSV_HEADER_CONVERTERS.items():
                dataframe_dict[csv_header].append(contact[breeze_header])

            if contact.get('tags') is not None:
                for tag in contact['tags']:
                    qualified_header = f'{tag} (Tag)'
                    dataframe_dict[qualified_header][index] = 'x'

        return pd.DataFrame(data=dataframe_dict)

    @classmethod
    def _get_failed_results_attachment_path(cls):
        path = cls._export_failed_sync_contacts()
        return path
