#!/usr/bin/env python3

import json
import os
import re
import datetime
import shutil
import sys
import matplotlib.pyplot as plt

from common_utils import *
from args import *


def sanitize_config(config, basename, dir_path):
    required_params = ['exec_cmd', 'targets']

    valid_buckets = ['second', 'minute', 'hour', 'sec', 'min', 'hour', 's', 'm', 'h']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    if len(config['targets']) == 0:
        danger("No target specified")
        return False

    if 'bucket' not in config or config['bucket'].lower() not in valid_buckets:
        warn("Invalid bucket unit")
        warn("Valid units are : %s" % ' '.join(valid_buckets))
        warn("setting to default value: min")
        config['bucket'] = 'min'

    # hard renaming
    config['output_file'] = dir_path + '/' + basename + '.report'

    if 'crash_name_pattern' not in config:
        warn("crash_name_pattern missing in config")
        warn('set to defalut value: [".+"]')
        config['crash_name_pattern'] = [".+"]

    if 'limit' not in config:
        warn("limit missing in config")
        warn('set to default valeu: 3600')
        config['limit'] = 3600

    if len(config['targets']) == 0:
        danger("No target specified")
        return False

    target_sanitized = False
    for target_name in config['targets']:
        target = config['targets'][target_name]
        target_sanitized = sanitize_target(target)

    return target_sanitized


def sanitize_target(target):
    required_params = ['crash_dirs']

    for param in required_params:
        if param not in target:
            danger("%s is missing in target" % param)
            return False

    if len(target['crash_dirs']) == 0:
        danger('No entry dir specified for target')
        return False

    else:
        # fuzzy finding
        fuzzy_stats_loc = ['/../fuzzer_stats', '/fuzzer_stats']
        stats_file_found = False
        stats_file = None
        dir_name = os.path.basename(os.path.dirname(target['crash_dirs'][0]))
        for entry_dir in target['crash_dirs']:
            for stats_loc in fuzzy_stats_loc:
                stats_file = os.path.abspath(entry_dir) + stats_loc
                if os.path.isfile(stats_file):
                    stats_file_found = True
                    break
            if stats_file_found:
                break

        if not stats_file_found and 'start_time' not in target:
            warn('Neither start_time or fuzzer_stats found')
            warn("Will try to get from the dir name")
            time_str = dir_name[-17:]
            try:
                timestamp = int(datetime.datetime.strptime(time_str, '%Y%m%d_%H_%M_%S').strftime("%s"))
                target['start_time'] = timestamp
            except:
                danger("cannot get start_time from dir name")
                return False
        elif stats_file_found:
            # coexistence allowed but warn user
            if 'start_time' in target:
                warn('Warning: both "start_time" and fuzzer_stats file exist! "fuzzer_stats" will be used.')
            with open(stats_file, 'r') as statsfile:
                for line in statsfile.readlines():
                    if re.search('start_time', line):
                        target['start_time'] = int(line.split()[2])
                        break
            if 'start_time' not in target:
                danger('Bad format: no "start_time" found in fuzzer_stats')
                return False

    return True


@timed
def main():
    arg_parser = ArgParser(description='Regularize the configuration report.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the configuration regularization utility")

    config_path = args.c

    config_path = os.path.abspath(config_path)

    if not os.path.isfile(config_path):
        danger("invalid config path")
        exit(1)

    dir_path = os.path.dirname(config_path)

    # dir_name = os.path.basename(dir_path)
    # info(dir_name)

    basename = os.path.basename(config_path)

    basename = os.path.splitext(basename)[0]

    backup_file = basename + "_backup.json"
    backup_path = dir_path + '/' + backup_file

    shutil.copyfile(config_path, backup_path)

    with open(backup_path) as backup_file:
        config = json.load(backup_file)
        if sanitize_config(config, basename, dir_path):
            with open(config_path,'w') as config_file:
                pp = json.dumps(config, indent=4, sort_keys=True)
                config_file.write(pp)


if __name__ == "__main__":
    main()