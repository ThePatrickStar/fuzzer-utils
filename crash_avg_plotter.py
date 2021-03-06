import json
import os
import re
import shutil
import sys
import matplotlib.pyplot as plt

from common_utils import *
from args import *


def sanitize_config(config):
    required_params = ['plot_file', 'targets', 'bucket']

    valid_buckets = ['second', 'minute', 'hour', 'sec', 'min', 'hour', 's', 'm', 'h']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    if config['bucket'].lower() not in valid_buckets:
        danger("Invalid bucket unit")
        danger("Valid units are : %s" % ' '.join(valid_buckets))
        return False

    if len(config['targets']) == 0:
        danger("No target specified")
        return False

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
    arg_parser = ArgParser(description='Analyze average unqiue crashes.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the average crash analysis utility")

    config_path = args.c

    with open(config_path) as config_file:
        config = json.load(config_file)
        if not sanitize_config(config):
            sys.exit(1)

        targets = config['targets']

        # key: target name; value: average crash no
        target_crash_dict = {}

        for target_key in targets:
            info("checking for %s" % target_key)
            target = targets[target_key]
            if not sanitize_target(target):
                danger("skipping")
                continue

            data_files = target['data_files']
            base_no = len(data_files)
            accumulates = []
            first_run = True

            for data_file in data_files:
                with open(data_file) as data_fd:
                    lines = data_fd.readlines()
                    for (i, line) in enumerate(lines):
                        tokens = line.split(',')
                        bin_no = int(tokens[0])
                        crash_no = int(tokens[1])
                        if bin_no != i+1:
                            danger("invalid file - bin_no(%d), line_no(%d)" % (bin_no, i))
                            sys.exit(1)
                        if first_run:
                            accumulates.append(crash_no)
                        else:
                            accumulates[i] += crash_no
                    first_run = False

            avgs = list(map(lambda acc: float(acc)/float(base_no), accumulates))
            target_crash_dict[target_key] = avgs

        # then we need to process the data and draw the plot
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # sort the group names, make sure every time the order is consistent
        group_names = list(target_crash_dict.keys())
        group_names.sort()

        for group_name in group_names:

            avgs = target_crash_dict[group_name]
            # max_bin = max(known_bins)
            max_bin = len(avgs)

            x_vals = []
            y_vals = []

            for bin_no in range(0, max_bin):
                x_vals.append(bin_no+1)
                y_vals.append(avgs[bin_no])

            ax.plot(x_vals, y_vals, label=group_name)

        bucket = config['bucket']
        edge_no_time_plot_filename = config['plot_file']
        ax.set(xlabel='time (%s)' % bucket, ylabel='avg unique crash no #',
               title='No of crashes found over time')
        ax.grid()
        ax.legend()

        fig.savefig(edge_no_time_plot_filename)
        # plt.show()


if __name__ == "__main__":
    main()
