import json
import os
import re
import shutil
import subprocess
import sys
import matplotlib.pyplot as plt

# TODO: deal with the dirty hack of importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *
from args import *
from entry import *


def sanitize_config(config):
    required_params = ['showmap_command', 'showmap_output', 'output_dir', 'entry_name_pattern',
                       'start_time', 'bucket']

    valid_buckets = ['second', 'minute', 'hour', 'sec', 'min', 'hour', 's', 'm', 'h']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    entry_dir_pattern = 'entry_dirs_.+'

    entry_groups = []

    for param in config:
        if re.fullmatch(entry_dir_pattern, param) is not None:
            entry_groups.append(param)

    if len(entry_groups) == 0:
        danger("No entry directory specified")
        return False

    if config['bucket'].lower() not in valid_buckets:
        danger("Invalid bucket unit")
        danger("Valid units are : %s" % ' '.join(valid_buckets))
        return False

    # some amendments to config
    if not config['output_dir'].endswith('/'):
        config['output_dir'] += '/'

    config['entry_groups'] = entry_groups

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

        start_time = int(config['start_time'])

        # default bucket margin is one hour
        bucket_margin = 3600
        bucket = config['bucket']
        if bucket.lower() in ['minute', 'min', 'm']:
            bucket_margin = 60
        elif bucket.lower() in ['second', 'sec', 's']:
            bucket_margin = 1

        # key: entry group name, value: edge_no_dict
        entry_group_dict = {}

        entry_groups = config['entry_groups']

        for entry_group in entry_groups:
            group_name = entry_group.replace('entry_dirs_', '')
            entry_dirs = config[entry_group]

            covered_edges = set()

            entries = []

            # key: bin_no, value: count
            edge_no_dict = {}

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
                if entry.bin_no not in edge_no_dict:
                    edge_no_dict[entry.bin_no] = len(covered_edges)
                else:
                    edge_no_dict[entry.bin_no] = len(covered_edges)

            entry_group_dict[group_name] = edge_no_dict
            ok("%s - Total number of covered edges: %d" % (group_name, len(covered_edges)))

        # then we need to process the data and draw the plot
        fig = plt.figure()
        ax = fig.add_subplot(111)

        for group_name in entry_group_dict:
            edge_no_dict = entry_group_dict[group_name]

            if 0 not in edge_no_dict:
                danger('Wrongly processed edge no dict!')
                sys.exit(1)

            known_bins = list(edge_no_dict.keys())
            known_bins.sort()
            max_bin = max(known_bins)

            x_vals = []
            y_vals = []

            for bin_no in range(0, max_bin+1):
                temp_bin_no = bin_no
                while temp_bin_no not in known_bins:
                    temp_bin_no -= 1
                x_vals.append(bin_no + 1)
                y_vals.append(edge_no_dict[temp_bin_no])

            ax.plot(x_vals, y_vals)

        edge_no_time_plot_filename = config['output_dir'] + '/' + "edge_no_over_time"
        ax.set(xlabel='time (%s)' % bucket, ylabel='edge no #',
               title='No of edges covered over time')
        ax.grid()

        fig.savefig(edge_no_time_plot_filename)
        # plt.show()


if __name__ == "__main__":
    main()
