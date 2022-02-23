
# Default auxiliary settings - can also be changed by the respective script arguments
DEFAULT_STRATEGY = '1'
DRY_RUN = 'no'
DEFAULT_EXPORT_CSV = 'yes'  # Not relevant to strategy 1

# Input paths
DEFAULT_DATA_INPUT_FILE_PATH = 'data_files/input/breeze.csv'
DEFAULT_SAMPLE_INPUT_FILE_PATH = 'data_files/input/sample.csv'
# Output paths
DATA_OUTPUT_FILE_NAME = 'contacts_to_sync.csv'
FAILED_SYNC_DATAFRAME_OUTPUT_FILE_NAME = 'failed_syncs.csv'

""" 
    This config governs the header mappings between the sample file (respond.io) and the data file (breeze),
    e.g. "the column with header X of the sample file is made up of columns Y and Z of the data file". 
    It also allows for column values to be dynamically calculated at runtime. 
    
    Note: For more than one column value mapping, the values are simply comma separated in the new column. 
    
    Configuration:
        'breeze_headers' => the Breeze headers/columns from which to consolidate the respond.io column value
        'lambda' => the function to call to add dynamically determined values in addition to 'breeze_headers'
        'default' => the default value when no other value is found
        
        Example:
        {
            <Sample File Header>: {
                'breeze_headers': [<breeze_header_1>, ...],       ---- optional
                'lambda': <function name>,                        ---- optional
                'default': <default value>,                       ---- optional
            }     
        }
        
    Notes:
    1) If a header mapping is not done, the script will assume the sample file header maps directly
       to the datafile header.
    2) You can map a header to an empty configuration (i.e. <Sample File Header>: {}) which will cause 
       the parsed column to be empty.
    3) You can add a 'default' value which the script will use to populate each cell with.
"""
HEADER_VALUE_MAPPINGS = {
    'Phone Number': {'breeze_headers': ['Mobile']},
    'Tags': {'lambda': 'dynamic_tags', 'breeze_headers': ['*(Tag)', 'Campus']},
    'Email': {'breeze_headers': ['Email']},
    'Assignee': {},
    'custom_field.breeze_id': {'breeze_headers': ['Breeze ID']},
    'custom_field.active': {'default': 'true'},
}


"""
    This configuration specifies which function is to be executed 
    on every row item for the specified columns. This is useful when you want
    to make sure, for example, that phone numbers are stored correctly.
    
    Note: each function specified must be declared in the DataCleaner class.
    
    INPUT_COLUMNS_CLEANING_FUNCTIONS will be executed on the input datafile's columns, hence the
    column names must correspond to the input file's column names.
    
    OUTPUT_COLUMNS_CLEANING_FUNCTIONS will be executed on the output datafile's columns, hence the
    column names must correspond to the output file's column names, i.e. the same columns as the sample file.
"""
INPUT_COLUMNS_CLEANING_FUNCTIONS = {
    'Mobile': 'clean_phone_number',
}

OUTPUT_COLUMNS_CLEANING_FUNCTIONS = {
    'Tags': 'clean_tags'
}


# DYNAMIC TAGS MANAGEMENT
# Below are tags that should be assigned dynamically
LEGENDES = 'Legendes'
MEMBER = 'Member'
VISITOR = 'Visitor'
FEMALE = 'Female'
MALE = 'Male'
TEMP_AGE_TAG = 'TempAgeTag'

# The values of this config MUST be formatted as follows
# <Tag name>: '`<column-name>` <operator> `<value>`'
DYNAMIC_TAGS_CRITERIA = {
    LEGENDES: "`Age` >= `65`",
    MALE: "`Gender` = `Male`",
    FEMALE: "`Gender` = `Female`",
    TEMP_AGE_TAG: "`Age` >= `16`"
}

# ---- FILTERED EXPORTING ----
# Filtering is tested very limited

# For no tags filtering, keep list empty
FILTERED_EXPORT_ENABLED = True
ONLY_EXPORT_CONTACTS_WITH_TAGS = [TEMP_AGE_TAG]

# When adding another column, a logical OR operator is applied
EXPORT_CONTACTS_WHERE_COLUMNS_HAS_VALUE = {
    'Tags': ONLY_EXPORT_CONTACTS_WITH_TAGS,
}

if FILTERED_EXPORT_ENABLED:
    FILTERED_EXPORT_ENABLED = any(EXPORT_CONTACTS_WHERE_COLUMNS_HAS_VALUE)


# ----- API CONFIGS -----

# This configuration setting determines by which custom field's value all remote contacts
# should be pulled, which will then be compared to the input data.
GET_BY_REMOTE_FIELD_NAME = 'active'
GET_BY_REMOTE_FIELD_VALUE = 'true'

# 'field_id' => the respond.io field id of the column. This will be used when the data is
#               mapped to the API structure.
API_FIELD_MAPPINGS = {
    'custom_field.breeze_id': {
        'field_id': 'breeze_id',
    },
    'Phone Number': {
        'field_id': 'phone',
    },
    # 'Email': {
    #     'field_id': 'email',
    # },
    'First Name': {
        'field_id': 'firstName',
    },
    'Last Name': {
        'field_id': 'lastName',
    },
    'custom_field.active': {
        'field_id': 'active',
    },
    'Tags': {  # This is an exception
        'field_id': 'tags'
    },
}

RESPONDIO_API_URL = 'https://app.respond.io/api/v1/'
RESPONDIO_API_TOKEN = 'f5b39f52ba96fdacf47f0b1fe145cf68c5ffcaf8fe5108cbab7c0e18b576ebc51342ace4f3ebac2eb89f268bf9c5c8e1176886778e302e8e24976acff77544d1'

BREEZE_API_URL = 'https://gesinskerk.breezechms.com/api/'
BREEZE_API_KEY = 'dd6bdc926910babb9e745163ee11b4d0'
