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
    required_params = ['targets', 'tools', 'bucket', 'output_dir', 'ylabel', 'file_postfix']

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


@timed
def main():
    arg_parser = ArgParser(description='Analyze leader of several tools.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the leader analysis utility")

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

        targets = config['targets']
        tools = config['tools']
        bucket = config['bucket']
        lines_no = 0
        # key: tool, value: lead list
        tool_lead_dict = {}
        # key: tool, value: {target: target_lines}
        tool_lines_dict = {}
        for tool in tools:
            tool_lead_dict[tool] = []

        for target in targets:
            for tool_key in tools:
                if tool_key not in tool_lines_dict:
                    tool_lines_dict[tool_key] = {}
                tool = tools[tool_key]
                tool_lines_file = tool[target]
                with open(tool_lines_file) as fd:
                    lines = fd.readlines()
                    tool_lines_dict[tool_key][target] = lines
                    lines_no = len(lines)

        for tool in tools:
            tool_lead_dict[tool] = [0] * lines_no

        for i in range(0, lines_no):
            for target in targets:
                max_val = 0
                for tool_key in tools:
                    if float(tool_lines_dict[tool_key][target][i]) > max_val:
                        max_val = float(tool_lines_dict[tool_key][target][i])
                for tool_key in tools:
                    if float(tool_lines_dict[tool_key][target][i]) == max_val:
                        tool_lead_dict[tool_key][i] += 1

        leader_fig_id = 1
        leader_fig = plt.figure(leader_fig_id)
        leader_ax = leader_fig.add_subplot(111, aspect=100)
        leader_fig.set_size_inches(8.5, 3.5)
        # leader_ax = leader_fig.add_subplot(111, aspect='equal')

        for tool_key in tool_lead_dict:

            leads = tool_lead_dict[tool_key]
            # max_bin = max(known_bins)
            max_bin = len(leads)

            x_vals = []
            y_vals = []

            for bin_no in range(0, max_bin):
                x_vals.append(bin_no)
                y_vals.append(leads[bin_no])

            if tool_key == 'Cerebro':
                leader_ax.plot(x_vals[1:], y_vals[1:], label=tool_key, linestyle='solid', color='xkcd:scarlet')
            elif tool_key == 'Cerebro-afl':
                leader_ax.plot(x_vals[1:], y_vals[1:], label=tool_key, linestyle='dashed', color='xkcd:slate blue')
            elif tool_key == 'aflfast':
                leader_ax.plot(x_vals[1:], y_vals[1:], label=tool_key, linestyle='dashdot', color='xkcd:olive yellow')
            else:
                leader_ax.plot(x_vals[1:], y_vals[1:], label=tool_key)

        # avg plot
        leader_plot_filename_pdf = config['output_dir'] + 'pdfs/leader' + config['file_postfix'] + '.pdf'
        leader_plot_filename_png = config['output_dir'] + 'pngs/leader' + config['file_postfix'] + '.png'
        leader_ax.set(xlabel='time (%s)' % bucket, ylabel=config['ylabel'])
        # avg_ax.grid()
        leader_ax.legend()
        leader_fig.savefig(leader_plot_filename_pdf)
        leader_fig.savefig(leader_plot_filename_png)


if __name__ == "__main__":
    main()
