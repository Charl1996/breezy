# Welcome to Breezy!

Breezy is simply a script that takes input, does some processing on the data and either spits out a .csv file or syncs it to a remote API (in this case respond.io).
 

## Setup
Before we can execute this amazing script, we have to make sure your environment is properly set up, i.e. that you have the
appropriate packages installed. Luckily a bash script has been supplied that does all this for you! Wow!

_"Start, where do I?"_ - (what Yoda would have asked)

If you're reading this it probably means you already have the following files/directories on your computer tugged away snugly in a folder
somewhere on your computer:
- requirements.txt
- sync.sh
- data_files/
    - input/
        - breeze.csv
        - sample.csv
    - output/
- /code
    - configs.py
    - main.py
    - strategies.py
    - respondio.py
    - utils.py

Now, assuming you have python and pip installed on your computer, you can set up your environment by running the following command in the shell
(make sure you run this from the directory in which the sync.sh file lives)

    bash sync.sh setup

The script will have installed the python virtualenv package for you, created and activated the virtual environment and installed all the relevant
python packages specified in the requirements.txt file.

_"Virtualenv, what is?"_ - asks Yoda again

The [virtualenv](https://realpython.com/python-virtual-environments-a-primer/) package handle python virtual environments for you. This means that packages that are installed in this virtual environment
will not affect other virtual environments' packages or even your system-wide packages. This amazing feature allows you to have
multiple projects on your computer with each project maintaining a potentially different version of the same package.

## Running the script
To execute the script, simpy run the following command

    bash sync.sh <argument1> ...

(Note that one or more arguments can be supplied when invoking the script, but they are all optional and in most cases not even necessary)

## Exploring the script

Currently, there exist two strategies of syncing the data. Both involves specifying a path to a .csv data file which will be 
read and processed by the script. The main difference between strategy 1 and strategy 2 is the way the processed data is handled.

Before we continue on this wonderful journey, please take the time to familiarize yourself with the jargon that's going to be used throughout this document.

## Jargon
- **Input data:** the data that is extracted from the input .csv file.
- **Processed data:** the input data that has been cleaned and formatted according to the sample file's format.
- **Processed columns:** similar to **Processed data**, but just referring to specifically the columns/headers (it's basically the sample file headers)

## Strategies
Now let's explore the two strategies in a bit more detail.
### Strategy 1
This strategy is the most straight-forward one. The strategy involves the following steps:
1) Read in data from the data file
2) Clean the data
3) Parse cleaned data to format corresponding to a sample file
4) Do post-processed data cleaning (if necessary)
5) Export the cleaned data to another .csv

The exported file in step 5 can be used to manually import the data to respond.io.

### Strategy 2
This strategy works exactly like Strategy 1, except for the way the cleaned data is handled (i.e. step 5). This strategy
instead pulls the remote data from respond.io and compares the processed data (source of truth) to the remote data, after which it syncs the 
remote data to the input data.

Now that you are an expert on how the strategies work, let's look at the different files that makes up the script. 

## File Layout
This section explains briefly the different python files that makes up the script.  

### main.py
This file handles the commandline inputs to the script and determines the appropriate strategy to execute in the **strategies.py** file.

### strategies.py
This file is the backbone of the different strategies as it contains the [classes](https://www.w3schools.com/python/python_classes.asp) that make up these strategies.
The two most important classes are (quite creatively) called
1) StrategyOne
2) StrategyTwo

#### StrategyOne
This class inherits from a different class called "BaseStrategy", which defines the basic methods that each strategy should implement. These methods include
1) _execute_ : this method is the entry point to the strategy class and defines the sequence of events of execution.
2) _get_data_ : this method defines the way in which data is being input to the script.
3) _clean_data_ : this method handles any data sanitizing.
4) _report_faulty_data_ : this method is used to report/notify the user of any erroneous data. 
5) _handle_cleaned_data_ : this method decides what to do with the data that has been cleaned.
6) _notify_results_ : this method is used to report/notify the user of the final results of the script.

#### StrategyTwo
This class inherits from the _StrategyOne_ class, meaning that all the functonality available to StrategyOne is also available to this class and
will in fact be executed unless the methods is overwritten in the _StrategyTwo_ class. Most notably, the _handle_cleaned_data_ method of 
this class is overwritten to sync the data to respond.io instead of simply exporting a .csv file. 

#### Other notable mentions
**DataCleaner** 
<br>
This class defines the cleaning function routines which will be called during the execution of the _clean_data_ routine.
As such, all methods that are expected to be executed during the _clean_data_ routine should be defined here. 
<br>
<br>
Note that the methods defined here takes a single parameter (in addition to the standard `cls` parameter); this parameter is the single 
value on which sanitizing operations needs to be applied. For instance, let's suppose you have a column called "Mobile" which contains the
mobile numbers of people, then the input argument to the corresponding cleaning function would be a single mobile number value.
<br>
<br>
The cleaning functions to be executed on each column is specified by the `INPUT_COLUMNS_CLEANING_FUNCTIONS` and `OUTPUT_COLUMNS_CLEANING_FUNCTIONS`
configurations respectively (see the **configs.py** section).

### respondio.py
This file is the script's interface to the respond.io [API](https://docs.respond.io/developer-api/contacts-api#create-contact).

### util.py
This is an utilities file which only contains functions that doesn't really fit in anywhere else...kinda like rebel functions, they
don't really fit in.

### configs.py
This file is the script's configuration file. This is the file you want to change if you want to make changes to
1) How data is read
2) How data is processed
3) Where data is read from
4) Where data is stored
5) What data is synced remotely

The different configuration settings is explained in detail below.

## Configuration settings

The configuration settings detemine the smaller details of the script, i.e. what data is cleaned, how data is cleaned, 
how data is formatted etc.

**DEFAULT_STRATEGY**<br>
Specifies which strategy should be executed when invoking the script. 

**DRY_RUN**<br>
Specifies whether a dry-run of the sync should be performed, meaning the actual sync will not happen, but rather
the data that will be synced will simply be output to the terminal. This is useful to check whether the script correctly identified
the sync data.

**DEFAULT_EXPORT_CSV**<br>
Specifies whether the cleaned data should be exported before syncing it remotely. The failed syncs will also
be output to a .csv file.
<br>
Note that this setting only applies to Strategy 2.

**DEFAULT_DATA_INPUT_FILE_PATH**<br>
Specifies a different data file to use instead of the default.

**DEFAULT_SAMPLE_INPUT_FILE_PATH**<br>
Specifies a different sample file to use instead of the default.

**DATA_OUTPUT_FILE_NAME**<br>
The file name of the output .csv file that contains the formatted processed data that can be used to manually import
to respond.io.

**FAILED_SYNC_DATAFRAME_OUTPUT_FILE_NAME**<br>
The file name of the output .csv file that contains the failed remote syncs.

**HEADER_VALUE_MAPPINGS**<br>
This setting governs the header mappings between the sample file and the data file. Think of it as
_"the column with header X of the sample file is made up of columns Y and Z of the data file"_. 
It also allows for column values to be dynamically calculated at runtime by specifying a function with the `lambda` setting.
The `default` setting specifies the default value in the event that no other value is found.

Format:

        {
            <Sample File Header>: {
                'breeze_headers': [<breeze_header_1>, ...],       ---- optional
                'lambda': <function name>,                        ---- optional
                'default': <default value>,                       ---- optional
            }     
        }

Important notes:
1) If a header mapping is not done, the script will assume the sample file header maps directly
   to the data file header.
2) You can map a header to an empty configuration (i.e. <Sample File Header>: {}) which will cause 
   the parsed column to be empty.


**INPUT_COLUMNS_CLEANING_FUNCTIONS**<br>
The cleaning functions that should be invoked on the rows of the specified columns during the cleaning routines of the input
data file. Note that the column name corresponds to the column name as seen in the input data file.

Format:

    {
        <input_file_column_name>: "<function_name>",
    }

**OUTPUT_COLUMNS_CLEANING_FUNCTIONS**<br>
The cleaning functions that should be invoked on the rows of the specified columns during the cleaning routines of the
reformatted processed file. Note that the column name corresponds to the column name as seen in the sample file (processed column name).

Format:

    {
        <sample_file_column_name>: "<function_name>",
    }

**DYNAMIC_TAGS_CRITERIA**<br>
This setting holds a list of column names mapping to criteria which should be executed upon the columns in order to detemine
whether the specified tag should be applied to the row item.

Format:

    {
        <tag_name>: "`column_name` <operator> `<value>`",
    }

(Note the backticks before and after the `column_name` and `value`)

**FILTERED_EXPORT_ENABLED**<br>
A setting that can be set to `True` or `False`, indicating whether the processed data should be filtered by the specified 
tags in the process.

**ONLY_EXPORT_CONTACTS_WITH_TAGS**<br>
Contains a list of tags by which the data should be filtered.

**EXPORT_CONTACTS_WHERE_COLUMNS_HAS_VALUE**<br>
This setting contains a list of processed column names mapping to values by which the data should be filtered. This setting
is not yet fully tested, so should be used with caution.

**GET_BY_REMOTE_FIELD_NAME**<br>
The `custom_field` name by which to search for remote respond.io contact the compare to the input data. It is best left as is.<br>
_**Only change this if you know what you are doing!**_

**GET_BY_REMOTE_FIELD_VALUE**<br> 
The `custom_field` value by which to search for remote respond.io contact the compare to the input data. It is best left as is.<br>
_**Only change this if you know what you are doing!**_

**API_FIELD_MAPPINGS** 
This setting maps the processed data column names to their respective respond.io api field id's. These field id's can be obtained
on the respond.io dashboard by going to Settings -> Contact fields.

Format:

    {
        <column_name>: {
            'field_id': <field_id>
        }
    }


## Commandline arguments

In addition to the configuration settings above, the following commandline arguments can be specified when invoking the script.
You can also run the script with `-h` to see a brief description of each of these arguments.

(note that all these arguments only changes the default configuration settings already specified in the _configs.py_ file)

**--strategy** : Overwrites the DEFAULT_STRATEGY setting. Usage: 
`source sync.sh --strategy <option>`
<br><br>
Options: `1`/`2`

**--sample** : Overwrites the DEFAULT_SAMPLE_INPUT_FILE_PATH setting. Usage: 
`source sync.sh --sample path/to/samplefile.csv`

**--data** : Overwites the DEFAULT_DATA_INPUT_FILE_PATH setting. Usage:
`source sync.sh --data path/to/datafile.csv`

**--export** : Overwrites the DEFAULT_EXPORT_CSV config setting.
Usage:
`source sync.sh --export <option>`
<br><br>
Options: `yes`/`no`

**--dry** : Overwrites the DRY_RUN config setting.
Usage:
`source sync.sh --dry <option>`
<br><br>
Options: `yes`/`no`

## Debugging issues
Bugs. It happens.

When you encounter a scenario in which the script errors out, you can debug what's happening by using a very nice in-built python
tool called `breakpoint`. It's very easy to use. Simply add the following line of code to wherever you want the script execution
to stop:

    breakpoint()

Once the execution has stopped here, you will see the following shell

    (Pdb) 

Once you see this, you are now "in the code", meaning you can inspect any variables' values and even alter their values before continuing execution.
To continue the execution, simply press `c`, or if you want to quit, press `q`.