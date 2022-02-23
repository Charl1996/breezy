import argparse
from configs import (
    DEFAULT_STRATEGY,
    DEFAULT_DATA_INPUT_FILE_PATH,
    DEFAULT_SAMPLE_INPUT_FILE_PATH,
    DEFAULT_EXPORT_CSV,
    DRY_RUN,
)

# Maps the specified strategy number to file
STRATEGIES = {
    '1': 'StrategyOne',
    '2': 'StrategyTwo',
}


def handle_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--strategy',
        default=DEFAULT_STRATEGY,
        choices=STRATEGIES.keys(),
        help='The strategy that will be used to process the data.\n'
             '[1] Given a data csv, process and output csv. '
             '[2] Given a data csv, process and automatically update persons on Respond.io. '
    )
    parser.add_argument(
        '--sample',
        default=DEFAULT_SAMPLE_INPUT_FILE_PATH,
        help='Specifies the path to the sample file used to extract the headers',
    )
    parser.add_argument(
        '--data',
        default=DEFAULT_DATA_INPUT_FILE_PATH,
        help='Specifies the path to the csv data file',
    )
    parser.add_argument(
        '--export',
        default=DEFAULT_EXPORT_CSV,
        choices=['yes', 'no'],
        help='Specifies whether a csv should be exported',
    )
    parser.add_argument(
        '--dry',
        default=DRY_RUN,
        choices=['yes', 'no'],
        help='Specifies whether this attempt is a dry run',
    )

    return parser.parse_args()


args = handle_arguments()

# Extract arguments
strategy_class = STRATEGIES[args.strategy]
sample_file = args.sample
data_file = args.data

if args.dry == 'yes':
    dry_run = True
if args.dry == 'no':
    dry_run = False

# Not applicable to Strategy 1
if args.export == 'yes':
    should_export = True
else:
    should_export = False

# Import appropriate strategy class
exec(f'from strategies import {strategy_class}')

print(f'Executing {strategy_class}')
# Execute strategy
errors = eval(f'{strategy_class}.execute(sample_file, datafile=data_file, export=should_export, dry_run=dry_run)')

# Notify results
exec(f'{strategy_class}.notify_results(errors)')
