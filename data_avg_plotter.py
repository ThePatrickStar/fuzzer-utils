import json
import os
import re
import shutil
import sys
import matplotlib.pyplot as plt
import numpy as np

from collections import OrderedDict
from common_utils import *
from args import *


def sanitize_config(config):
    required_params = ['targets', 'bucket', 'output_dir', 'project', 'ylabel', 'file_postfix']

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
    arg_parser = ArgParser(description='Analyze average data of multiple files.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the multi-run analysis utility")

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

        # key: target name; value: average no
        target_avg_dict = {}
        # key: target name; value: {id: average no}
        target_detail_dict = {}
        # key: target name; value: min no
        target_min_dict = {}
        # key: target name; value: max no
        target_max_dict = {}

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

            target_details = OrderedDict()

            for (did, data_file) in enumerate(data_files):
                target_details[did] = []
                with open(data_file) as data_fd:
                    lines = data_fd.readlines()
                    for (i, line) in enumerate(lines):
                        tokens = line.split(',')
                        bin_no = int(tokens[0])
                        edge_no = int(tokens[1])
                        if bin_no != i+1:
                            danger("invalid file - bin_no(%d), line_no(%d)" % (bin_no, i), 1)
                            sys.exit(1)
                        target_details[did].append(edge_no)
                        if bin_no == len(lines):
                            ok("%s: %d" % (data_file, edge_no), 1)
                        if first_run:
                            accumulates.append(edge_no)
                        else:
                            accumulates[i] += edge_no
                    first_run = False

            mins = target_details[did]
            maxes = target_details[did]
            for did in target_details:
                tmp_details = target_details[did]
                mins = list(np.minimum(mins, tmp_details))
                maxes = list(np.maximum(maxes, tmp_details))

            target_min_dict[target_key] = mins
            target_max_dict[target_key] = maxes
            target_detail_dict[target_key] = target_details

            avgs = list(map(lambda acc: float(acc)/float(base_no), accumulates))
            ok("total avg: %.2f" % avgs[-1], 1)
            target_avg_dict[target_key] = avgs

        # then we need to process the data and draw the plot
        avg_fig_id = 1
        min_max_fig_id = 2
        detail_fig_id = 3
        avg_fig = plt.figure(avg_fig_id)
        avg_ax = avg_fig.add_subplot(111)
        min_max_fig = plt.figure(min_max_fig_id)
        min_max_ax = min_max_fig.add_subplot(111)

        # sort the group names, make sure every time the order is consistent
        group_names = list(target_avg_dict.keys())
        group_names.sort()
        bucket = config['bucket']

        for group_name in group_names:

            avgs = target_avg_dict[group_name]
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

            mins = target_min_dict[group_name]
            maxes = target_max_dict[group_name]
            max_bin = min(len(mins), len(maxes))
            x_vals = []
            min_vals = []
            max_vals = []
            for bin_no in range(0, max_bin):
                x_vals.append(bin_no)
                min_vals.append(mins[bin_no])
                max_vals.append(maxes[bin_no])
            if group_name == 'fot-pot':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:scarlet', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:scarlet', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:scarlet', alpha=0.3)
            elif group_name == 'fot-cov':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:slate blue', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:slate blue', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:slate blue', alpha=0.3)
            elif group_name == 'aflfast':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:olive yellow', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:olive yellow', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:olive yellow', alpha=0.3)
            else:
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', alpha=0.5)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', alpha=0.5)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name)

            detail_fig = plt.figure(detail_fig_id)
            detail_ax = detail_fig.add_subplot(111)

            target_detail = target_detail_dict[group_name]
            for did in target_detail:
                details = target_detail[did]
                max_bin = len(details)
                x_vals = []
                y_vals = []
                for bin_no in range(0, max_bin):
                    x_vals.append(bin_no)
                    y_vals.append(details[bin_no])
                detail_ax.plot(x_vals[1:], y_vals[1:], label=group_name+'-'+str(did))

            detail_plot_filename = config['output_dir'] + config['project'] + '-' + group_name + config['file_postfix']
            detail_ax.set(xlabel='time (%s)' % bucket, ylabel=config['ylabel'])
            detail_ax.legend()
            detail_fig.savefig(detail_plot_filename)

            detail_fig_id += 1

        avg_plot_filename = config['output_dir'] + config['project'] + config['file_postfix']
        avg_ax.set(xlabel='time (%s)' % bucket, ylabel='avg ' + config['ylabel'])
        # avg_ax.grid()
        avg_ax.legend()
        avg_fig.savefig(avg_plot_filename)

        min_max_plot_filename = config['output_dir'] + config['project'] + '-range' + config['file_postfix']
        min_max_ax.set(xlabel='time (%s)' % bucket, ylabel='range of ' + config['ylabel'])
        # avg_ax.grid()
        min_max_ax.legend(loc=0)
        min_max_fig.savefig(min_max_plot_filename)
        # plt.show()


if __name__ == "__main__":
    main()
