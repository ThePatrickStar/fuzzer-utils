import json
import os
import sys
from collections import OrderedDict
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *


def stoi_helper(astr):
    if astr == "average":
        return -1
    elif astr == "count":
        return -2
    else:
        return int(astr)


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
    required_params = ['data_files', 'output_file']

    for param in required_params:
        if param not in target:
            danger("%s is missing in target" % param)
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

            input_data_list = []
            for data_file in data_files:
                try:
                    with open(data_file) as data_fd:
                        input_data_list.append(json.load(data_fd))
                except Exception as e:
                    danger("Failed to load {0}".format(data_file))
            count = len(input_data_list)
            if count == 0:
                danger("No data file has been loaded successfully, skip this target: {0}".format(target_key))
                continue

            # switch [{edge: {5:{},10:{},20:{}}, func:{5:{},10:{},20:{}}, time:{5:{},10:{},20:{}} }]
            # to {edge: { 5: [{}], 10: [{}], 20: [{}] }, func: ..., time: ... }
            result_dict = {"edge": OrderedDict(), "func": OrderedDict(), "time": OrderedDict(),
                           "rank_nums": OrderedDict(), "total_bonus": OrderedDict(), "total_score": OrderedDict(),
                           "file_len": OrderedDict(), "edge_num": OrderedDict(), "func_num": OrderedDict()}
            # loop over 'edge' 'func' 'time' 'rank_nums' 'total_bonus' 'total_score'
            for paramkey in input_data_list[0].keys():
                cycle_numbers = sorted(input_data_list[0][paramkey].keys(), key=lambda x: int(x))
                log("{0:20} [cycle {1}]".format(paramkey, ",".join(cycle_numbers)))
                for cycle_num in cycle_numbers:  # loop over cycle5, 10, 20, ...
                    result_dict[paramkey][cycle_num] = OrderedDict()
                    sum_list = [each_dict[paramkey][cycle_num] for each_dict in input_data_list]
                    # if cycle_num not in shared_ranks:
                    #    shared_ranks[cycle_num] = sorted({stoi_helper(each_rank) for each_rank in sum_list[0].keys()}.intersection(*[ {stoi_helper(each_rank) for each_rank in each_dict} for each_dict in sum_list]))
                    shared_ranks = sorted({stoi_helper(each_rank) for each_rank in sum_list[0].keys()}.intersection(
                        *[{stoi_helper(each_rank) for each_rank in each_dict} for each_dict in sum_list]))
                    for index, rank in enumerate(shared_ranks):
                        if rank == -1:
                            shared_ranks[index] = "average"
                            break
                        elif rank == -2:
                            shared_ranks[index] = "count"
                            break
                    for each_shared_rank in shared_ranks:
                        sum_of_values = 0
                        for each_dict in sum_list:
                            sum_of_values += each_dict[str(each_shared_rank)]
                        result_dict[paramkey][cycle_num][each_shared_rank] = round(sum_of_values / count, 4)

            with open(output_file, 'w') as output_json:
                json.dump(result_dict, output_json)


if __name__ == "__main__":
    main()
