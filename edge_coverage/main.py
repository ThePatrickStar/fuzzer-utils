import json
import os
import re
import shutil
import subprocess
import sys

# TODO: deal with the dirty hack of importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *
from args import *
from entry import *
from edge_time_plotter import *
from entry_time_plotter import *
from worker import *
from data_collector import *


def sanitize_config(config):
    required_params = ['showmap_command', 'targets', 'showmap_output', 'output_dir', 'entry_name_pattern', 'bucket']

    valid_buckets = ['second', 'minute', 'hour', 'sec', 'min', 'hour', 's', 'm', 'h']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    if len(config['targets']) == 0:
        danger("No target specified")
        return False

    if config['bucket'].lower() not in valid_buckets:
        danger("Invalid bucket unit")
        danger("Valid units are : %s" % ' '.join(valid_buckets))
        return False

    # some amendments to config
    if not config['output_dir'].endswith('/'):
        config['output_dir'] += '/'

    if 'plot_figure' not in config:
        config['plot_figure'] = True

    return True


def sanitize_target(target):
    required_params = ['entry_dirs']

    for param in required_params:
        if param not in target:
            danger("%s is missing in target")
            return False

    if len(target['entry_dirs']) == 0:
        danger('No entry dir specified for target')
        return False

    else:
        # fuzzy finding
        fuzzy_stats_loc = ['/../fuzzer_stats', '/fuzzer_stats']
        stats_file_found = False
        stats_file = None
        for entry_dir in target['entry_dirs']:
            for stats_loc in fuzzy_stats_loc:
                stats_file = os.path.abspath(entry_dir) + stats_loc
                if os.path.isfile(stats_file):
                    stats_file_found = True
                    break
            if stats_file_found:
                break

        if not stats_file_found and 'start_time' not in target:
            danger('Neither start_time or fuzzer_stats found')
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
    arg_parser = ArgParser(description='Analyze edge coverage.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the edge coverage utility")

    config_path = args.c

    with open(config_path) as config_file:
        config = json.load(config_file)
        if not sanitize_config(config):
            sys.exit(1)

        if os.path.isdir(config['output_dir']):
            warn("output dir %s exists, we will clear it this time" % config['output_dir'])
            shutil.rmtree(config['output_dir'])

        os.makedirs(config['output_dir'])

        # default bucket margin is one hour
        bucket_margin = 3600
        bucket = config['bucket']
        if bucket.lower() in ['minute', 'min', 'm']:
            bucket_margin = 60
        elif bucket.lower() in ['second', 'sec', 's']:
            bucket_margin = 1

        # key: entry group name, value: edge_no_dict
        edge_group_dict = {}
        # key: entry group name, value: entry_no_dict
        entry_group_dict = {}

        targets = config['targets']

        workers = []

        # temporarily create a worker for every target
        for (i, target_key) in enumerate(targets.keys()):
            # info("checking for %s" % target_key)
            target = targets[target_key]
            target['name'] = target_key
            worker = Worker(i, [target], config, bucket_margin)
            workers.append(worker)

        ok("starting %d workers" % len(workers))
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        for worker in workers:
            for group in worker.edge_group_dict:
                edge_group_dict[group] = worker.edge_group_dict[group]
            for group in worker.entry_group_dict:
                entry_group_dict[group] = worker.entry_group_dict[group]

        if bucket_margin == 3600:
            bucket_margin = 1
        elif bucket_margin == 1:
            bucket_margin = 3600

        if config['plot_figure']:
            plot_edge_over_time(config, edge_group_dict, bucket, bucket_margin, 1)
            plot_entry_over_time(config, entry_group_dict, bucket, bucket_margin, 2)

        collect_entry_over_time(config, entry_group_dict, bucket_margin)
        collect_edge_over_time(config, edge_group_dict, bucket_margin)


if __name__ == "__main__":
    main()
