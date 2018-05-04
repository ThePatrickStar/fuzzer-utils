#!/usr/bin/env python3

import json
import os
import re
import shutil
import sys
import matplotlib.pyplot as plt

from collections import OrderedDict
from common_utils import *
from args import *


def sanitize_config(config):
    required_params = ['targets', 'bucket', 'output_dir', 'project']

    valid_buckets = ['second', 'minute', 'hour', 'sec', 'min', 'hour', 's', 'm', 'h']

    missing = False

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            missing = True

    if missing:
        return False

    if config['bucket'].lower() not in valid_buckets:
        danger("Invalid bucket unit")
        danger("Valid units are : %s" % ' '.join(valid_buckets))
        return False

    if len(config['targets']) == 0:
        danger("No target specified")
        return False

    if not config['output_dir'].endswith('/'):
        config['output_dir'] += '/'

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
    arg_parser = ArgParser(description='Analyze average edge coverage.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the average edge coverage analysis utility")

    config_path = args.c

    with open(config_path) as config_file:
        config = json.load(config_file)
        if not sanitize_config(config):
            sys.exit(1)

        if os.path.isdir(config['output_dir']):
            warn("output dir %s exists, we will clear it this time" % config['output_dir'])
            shutil.rmtree(config['output_dir'])

        os.makedirs(config['output_dir'])

        targets = config['targets']

        # key: target name; value: average edge no
        target_avg_edge_dict = {}
        # key: target name; value: {id: average edge no}
        target_detail_edge_dict = {}

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
            max_bin = config['max_bin']

            target_detail_edge_dict[target_key] = OrderedDict()

            for (did, data_file) in enumerate(data_files):
                target_detail_edge_dict[target_key][did] = []
                with open(data_file) as data_fd:
                    lines = data_fd.readlines()
                    for (i, line) in enumerate(lines):
                        tokens = line.split(',')
                        bin_no = int(tokens[0])
                        edge_no = int(tokens[1])
                        if bin_no != i+1:
                            danger("invalid file - bin_no(%d), line_no(%d)" % (bin_no, i), 1)
                            sys.exit(1)
                        target_detail_edge_dict[target_key][did].append(edge_no)
                        if bin_no == len(lines):
                            ok("%s: %d" % (data_file, edge_no), 1)
                        if first_run:
                            accumulates.append(edge_no)
                        else:
                            accumulates[i] += edge_no
                    first_run = False

            avgs = list(map(lambda acc: float(acc)/float(base_no), accumulates))
            ok("total avg: %.2f" % avgs[-1], 1)
            target_avg_edge_dict[target_key] = avgs

        # then we need to process the data and draw the plot
        avg_fig_id = 1
        detail_fig_id = 2
        avg_fig = plt.figure(avg_fig_id)
        avg_ax = avg_fig.add_subplot(111)

        # sort the group names, make sure every time the order is consistent
        group_names = list(target_avg_edge_dict.keys())
        group_names.sort()
        bucket = config['bucket']

        for group_name in group_names:

            avgs = target_avg_edge_dict[group_name]
            # max_bin = max(known_bins)
            max_bin = len(avgs)

            x_vals = []
            y_vals = []

            for bin_no in range(0, max_bin):
                x_vals.append(bin_no)
                y_vals.append(avgs[bin_no])

            if group_name == 'fot-pot':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='solid', color='xkcd:scarlet')
            elif group_name == 'fot-cov':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dashed', color='xkcd:slate blue')
            elif group_name == 'aflfast':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dashdot', color='xkcd:olive yellow')
            else:
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name)

            detail_fig = plt.figure(detail_fig_id)
            detail_ax = detail_fig.add_subplot(111)

            target_detail = target_detail_edge_dict[group_name]
            for did in target_detail:
                details = target_detail[did]
                max_bin = len(details)
                x_vals = []
                y_vals = []
                for bin_no in range(0, max_bin):
                    x_vals.append(bin_no)
                    y_vals.append(details[bin_no])
                detail_ax.plot(x_vals[1:], y_vals[1:], label=group_name+'-'+str(did))

            detail_plot_filename = config['output_dir'] + config['project'] + '-' + group_name + '-edge-time.pdf'
            detail_ax.set(xlabel='time (%s)' % bucket, ylabel='edge no #')
            detail_ax.legend()
            detail_fig.savefig(detail_plot_filename)

            detail_fig_id += 1

        avg_plot_filename = config['output_dir'] + config['project'] + '-edge-time.pdf'
        avg_ax.set(xlabel='time (%s)' % bucket, ylabel='avg edge no #')
        # avg_ax.grid()
        avg_ax.legend()

        avg_fig.savefig(avg_plot_filename)
        # plt.show()


if __name__ == "__main__":
    main()
