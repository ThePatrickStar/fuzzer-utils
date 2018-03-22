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

    return True


def sanitize_target(target):
    required_params = ['entry_dirs', 'start_time']

    for param in required_params:
        if param not in target:
            danger("%s is missing in target")
            return False

    if len(target['entry_dirs']) == 0:
        danger('No entry dir specified for target')
        return False

    return True


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

        base_command = config['showmap_command'].replace('##', config['showmap_output'])

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

        for target_key in targets:
            info("checking for %s" % target_key)
            target = targets[target_key]
            if not sanitize_target(target):
                danger("skipping")
                continue
            start_time = int(target['start_time'])
            group_name = target_key
            entry_dirs = target['entry_dirs']

            covered_edges = set()

            entries = []

            # key: bin_no, value: edge count
            edge_no_dict = {}
            # key: bin_no, value: entry count
            entry_no_dict = {}

            # collect entry files first
            for entry_dir in entry_dirs:
                entry_files = os.listdir(entry_dir)

                for entry_file in entry_files:
                    # we only check the fuzzer output file
                    for pattern in config['entry_name_pattern']:
                        if re.fullmatch(pattern, entry_file) is not None:
                            entry_file = entry_dir + '/' + entry_file

                            entry_mtime = int(os.stat(entry_file).st_mtime)

                            bin_no = int((entry_mtime - start_time)/bucket_margin)

                            entry = Entry(entry_file, entry_mtime, bin_no)

                            entries.append(entry)

                            break

            # sort the entry file list according to creation time
            entries.sort(key=lambda x: x.m_time, reverse=False)

            checked_entries = []

            # check each entry file
            for entry in entries:
                # info("checking %s -- %d" % (entry.path, entry.m_time), 1)

                temp_command = base_command.replace('@@', entry.path)
                proc = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                proc.communicate()

                with open(config['showmap_output']) as showmap_output_file:
                    lines = showmap_output_file.readlines()
                    for line in lines:
                        try:
                            edge_id = int(line.split(':')[0])
                            edge_count = int(line.split(':')[1])
                            covered_edges.add(edge_id)
                        except IndexError:
                            warn("cannot handle showmap output line: %s" % line, 1)

                # update the edge_no dict
                # NOTE: temporarily no difference
                checked_entries.append(entry)
                entry_no_dict[entry.bin_no] = len(checked_entries)

                if entry.bin_no not in edge_no_dict:
                    edge_no_dict[entry.bin_no] = len(covered_edges)
                else:
                    edge_no_dict[entry.bin_no] = len(covered_edges)

            edge_group_dict[group_name] = edge_no_dict
            entry_group_dict[group_name] = entry_no_dict
            ok("%s - Total number of covered edges: %d" % (group_name, len(covered_edges)))
            ok("%s - Total number of entries: %d" % (group_name, len(checked_entries)))

        plot_edge_over_time(config, edge_group_dict, bucket, bucket_margin, 1)
        plot_entry_over_time(config, entry_group_dict, bucket, bucket_margin, 2)


if __name__ == "__main__":
    main()
