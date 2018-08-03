#!/usr/bin/env python3

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

    if 'limit' not in config:
        config['limit'] = None
    else:
        config['limit'] = int(config['limit'])

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


@timed
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
        os.makedirs(config['output_dir'] + 'pdfs')
        os.makedirs(config['output_dir'] + 'pngs')
        os.makedirs(config['output_dir'] + 'txts')

        targets = config['targets']

        # key: target name; value: average nos
        target_avgs_dict = {}
        # key: target name; value: {id: average nos}
        target_details_dict = {}
        # key: target name; value: min nos
        target_mins_dict = {}
        # key: target name; value: max nos
        target_maxes_dict = {}
        # key: target name; value: average no
        target_avg_dict = {}

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

            target_mins_dict[target_key] = mins
            target_maxes_dict[target_key] = maxes
            target_details_dict[target_key] = target_details

            avgs = list(map(lambda acc: float(acc)/float(base_no), accumulates))
            ok("total avg: %.2f" % avgs[-1], 1)
            target_avg_dict[target_key] = avgs[-1]
            target_avgs_dict[target_key] = avgs

        # then we need to process the data and draw the plot
        avg_fig_id = 1
        min_max_fig_id = 2
        mix_fig_id = 3
        detail_fig_id = 4
        avg_fig = plt.figure(avg_fig_id)
        avg_ax = avg_fig.add_subplot(111)
        mix_fig = plt.figure(mix_fig_id)
        mix_ax = mix_fig.add_subplot(111)
        min_max_fig = plt.figure(min_max_fig_id)
        min_max_ax = min_max_fig.add_subplot(111)

        # sort the group names, make sure every time the order is consistent
        group_names = list(target_avgs_dict.keys())
        group_names.sort()
        bucket = config['bucket']

        for group_name in group_names:

            avgs = target_avgs_dict[group_name]
            # max_bin = max(known_bins)
            max_bin = len(avgs)

            if config['limit'] is not None:
                if max_bin > config['limit']:
                    max_bin = config['limit']

            x_vals = []
            y_vals = []

            for bin_no in range(0, max_bin):
                x_vals.append(bin_no)
                y_vals.append(avgs[bin_no])

            if group_name == 'Cerebro':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='solid', color='xkcd:scarlet')
            elif group_name == 'Cerebro-afl':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dashed', color='xkcd:slate blue')
            elif group_name == 'aflfast':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dashdot', color='xkcd:olive yellow')
            elif group_name == 'afl':
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle=':', color='xkcd:slate grey')
            else:
                avg_ax.plot(x_vals[1:], y_vals[1:], label=group_name)

            mins = target_mins_dict[group_name]
            maxes = target_maxes_dict[group_name]
            max_bin = min(len(mins), len(maxes))

            if config['limit'] is not None:
                if max_bin > config['limit']:
                    max_bin = config['limit']

            x_vals = []
            min_vals = []
            max_vals = []
            for bin_no in range(0, max_bin):
                x_vals.append(bin_no)
                min_vals.append(mins[bin_no])
                max_vals.append(maxes[bin_no])
            if group_name == 'Cerebro':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:scarlet', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:scarlet', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:scarlet', alpha=0.3)
            elif group_name == 'Cerebro-afl':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:slate blue', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:slate blue', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:slate blue', alpha=0.3)
            elif group_name == 'aflfast':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:olive yellow', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:olive yellow', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:olive yellow', alpha=0.3)
            elif group_name == 'afl':
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', color='xkcd:slate grey', alpha=0.8)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', color='xkcd:slate grey', alpha=0.8)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name, facecolor='xkcd:slate grey', alpha=0.3)
            else:
                min_max_ax.plot(x_vals[1:], min_vals[1:], linestyle='dotted', alpha=0.5)
                min_max_ax.plot(x_vals[1:], max_vals[1:], linestyle='dotted', alpha=0.5)
                min_max_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], label=group_name)

            if group_name == 'Cerebro':
                mix_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='solid', color='xkcd:scarlet')
                mix_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], facecolor='xkcd:scarlet', alpha=0.2)
            elif group_name == 'Cerebro-afl':
                mix_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dashed', color='xkcd:slate blue')
                mix_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], facecolor='xkcd:slate blue', alpha=0.2)
            elif group_name == 'aflfast':
                mix_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dashdot', color='xkcd:olive yellow')
                mix_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], facecolor='xkcd:olive yellow', alpha=0.2)
            elif group_name == 'afl':
                mix_ax.plot(x_vals[1:], y_vals[1:], label=group_name, linestyle='dotted', color='xkcd:slate grey')
                mix_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], facecolor='xkcd:slate grey', alpha=0.2)
            else:
                mix_ax.plot(x_vals[1:], y_vals[1:], label=group_name)
                mix_ax.fill_between(x_vals[1:], min_vals[1:], max_vals[1:], alpha=0.2)

            detail_fig = plt.figure(detail_fig_id)
            detail_ax = detail_fig.add_subplot(111)

            target_detail = target_details_dict[group_name]
            for did in target_detail:
                details = target_detail[did]
                max_bin = len(details)

                if config['limit'] is not None:
                    if max_bin > config['limit']:
                        max_bin = config['limit']

                x_vals = []
                y_vals = []
                for bin_no in range(0, max_bin):
                    x_vals.append(bin_no)
                    y_vals.append(details[bin_no])
                detail_ax.plot(x_vals[1:], y_vals[1:], label=group_name+'-'+str(did))

            detail_plot_filename_pdf = config['output_dir'] + 'pdfs/' + config['project'] + '-' + group_name + config['file_postfix'] + '.pdf'
            detail_plot_filename_png = config['output_dir'] + 'pngs/' + config['project'] + '-' + group_name + config['file_postfix'] + '.png'
            detail_ax.set(xlabel='time (%s)' % bucket, ylabel=config['ylabel'])
            detail_ax.legend()
            detail_fig.savefig(detail_plot_filename_pdf)
            detail_fig.savefig(detail_plot_filename_png)

            detail_fig_id += 1

        # avg plot
        avg_plot_filename_pdf = config['output_dir'] + 'pdfs/' + config['project'] + config['file_postfix'] + '.pdf'
        avg_plot_filename_png = config['output_dir'] + 'pngs/' + config['project'] + config['file_postfix'] + '.png'
        avg_ax.set(xlabel='time (%s)' % bucket, ylabel='avg ' + config['ylabel'])
        # avg_ax.grid()
        avg_ax.legend()
        avg_fig.savefig(avg_plot_filename_pdf)
        avg_fig.savefig(avg_plot_filename_png)

        # mix plot
        mix_plot_filename_pdf = config['output_dir'] + 'pdfs/' + config['project'] + '-mix' + config['file_postfix'] + '.pdf'
        mix_plot_filename_png = config['output_dir'] + 'pngs/' + config['project'] + '-mix' + config['file_postfix'] + '.png'
        mix_ax.set(xlabel='time (%s)' % bucket, ylabel='avg ' + config['ylabel'])
        # avg_ax.grid()
        mix_ax.legend()
        mix_fig.savefig(mix_plot_filename_pdf)
        mix_fig.savefig(mix_plot_filename_png)

        # min max plot
        min_max_plot_filename_pdf = config['output_dir'] + 'pdfs/' + config['project'] + '-range' + config['file_postfix'] + '.pdf'
        min_max_plot_filename_png = config['output_dir'] + 'pngs/' + config['project'] + '-range' + config['file_postfix'] + '.png'
        min_max_ax.set(xlabel='time (%s)' % bucket, ylabel='range of ' + config['ylabel'])
        # avg_ax.grid()
        min_max_ax.legend(loc=0)
        min_max_fig.savefig(min_max_plot_filename_pdf)
        min_max_fig.savefig(min_max_plot_filename_png)
        # plt.show()

        # backup the used data
        for group_name in group_names:
            target_details = target_details_dict[group_name]
            for did in target_details:
                data_file_name = config['output_dir'] + 'txts/' + group_name + '-' + str(did) + '.txt'
                details = target_details[did]
                with open(data_file_name, 'w') as data_fd:
                    for detail in details:
                        data_fd.write(str(detail) + '\n')
            data_file_name = config['output_dir'] + 'txts/' + group_name + '-avg' + '.txt'
            with open(data_file_name, 'w') as data_fd:
                avgs = target_avgs_dict[group_name]
                for avg in avgs:
                    data_fd.write(str(avg) + '\n')
        data_file_name = config['output_dir'] + 'txts/' + 'overall-avg' + '.txt'
        with open(data_file_name, 'w') as data_fd:
            for group_name in group_names:
                data_fd.write(group_name + ':' + str(target_avg_dict[group_name]) + '\n')


if __name__ == "__main__":
    main()
