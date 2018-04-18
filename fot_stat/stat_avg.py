import json
import os
import sys
import argparse
from functools import reduce

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *


def sanitize_config(config):
    required_params = ['targets']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    if len(config['targets']) == 0:
        danger("No target specified")
        return False

    if 'max_bin' not in config:
        config['max_bin'] = -1

    return True


def sanitize_target(target):
    required_params = ['data_files']

    for param in required_params:
        if param not in target:
            danger("%s is missing in target")
            return False

    if len(target['data_files']) == 0:
        danger('No data file specified for target')
        return False

    return True


def main():
    arg_parser = argparse.ArgumentParser(description='Analyze average edge coverage.')
    arg_parser.add_argument('-c', metavar='config_file', help='Path to the configuration json file.', required=True)

    args = arg_parser.parse_args()

    info("Welcome to use the average rank analysis utility")

    config_path = args.c

    with open(config_path) as config_file:
        config = json.load(config_file)
        if not sanitize_config(config):
            sys.exit(1)

        targets = config['targets']

        for target_key in targets:
            info("checking for %s" % target_key)
            target = targets[target_key]
            if not sanitize_target(target):
                danger("skipping")
                continue

            data_files = target['data_files']
            output_file = target['output_file']
            base_no = len(data_files)
            accumulates = []
            first_run = True
            max_bin = config['max_bin']

            input_data_list = []
            for data_file in data_files:
                with open(data_file) as data_fd:
                    input_data_list.append(json.load(data_fd))
                    count = len(input_data_list)

            # switch [{block: {5:{},10:{},20:{}}, func:{5:{},10:{},20:{}}, time:{5:{},10:{},20:{}} }]
            # to {block: { 5: [{}], 10: [{}], 20: [{}] }, func: ..., time: ... }
            result_dict = { "block": {}, "func":{}, "time":{} }
            for paramkey in input_data_list[0].keys(): # loop over 'block' 'func' 'time'
                for cycle_num in input_data_list[0][paramkey].keys(): # loop over cycle5, 10, 20
                    result_dict[paramkey][cycle_num] = dict()
                    sum_list = [each_dict[paramkey][cycle_num] for each_dict in input_data_list]
                    # CAN BE OPTIMIZED: here shared_ranks computed 9 times, but
                    # the 3 different paramkey with the same cycle_num have
                    # the same shared_ranks.
                    # here convert to integer for sorting by rank
                    # shared_ranks = sorted(set(sum_list[0].keys()).intersection(*[set(each_dict.keys()) for each_dict in sum_list]))
                    shared_ranks = sorted({int(each_rank) for each_rank in sum_list[0].keys()}.intersection(*[ {int(each_rank) for each_rank in each_dict} for each_dict in sum_list]))
                    for each_shared_rank in shared_ranks:
                        sum_of_values = 0
                        for each_dict in sum_list:
                            sum_of_values += each_dict[str(each_shared_rank)]
                            result_dict[paramkey][cycle_num][each_shared_rank] = round(sum_of_values / count, 4)

            with open(output_file, 'w') as output_json:
                json.dump(result_dict, output_json)


if __name__ == "__main__":
    main()
