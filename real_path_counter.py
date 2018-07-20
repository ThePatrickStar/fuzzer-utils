import json
import os
import re
import shutil
import subprocess
import sys
import matplotlib.pyplot as plt

from common_utils import *
from args import *
from edge_coverage.entry import *


def sanitize_config(config):
    required_params = ['execute_command', 'targets', 'false_path_pattern', 'output_dir', 'entry_name_pattern', 'bucket']

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
    required_params = ['entry_dirs', 'need_execution']

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
            warn('Neither start_time or fuzzer_stats found, will use the earliest m_time as the start time.')
            target['start_time'] = None
            return True
        elif stats_file_found:
            # coexistence allowed but warn user
            if 'start_time' in target:
                warn('both "start_time" and fuzzer_stats file exist! "fuzzer_stats" will be used.')
            with open(stats_file, 'r') as statsfile:
                for line in statsfile.readlines():
                    if re.search('start_time', line):
                        target['start_time'] = int(line.split()[2])
                        break
            if 'start_time' not in target:
                danger('Bad format: no "start_time" found in fuzzer_stats')
                return False

    return True


def plot_entry_over_time(config, entry_group_dict, bucket, bucket_margin, fig_no):
    # then we need to process the data and draw the plot
    fig = plt.figure(fig_no)
    ax = fig.add_subplot(111)

    # sort the group names, make sure every time the order is consistent
    group_names = list(entry_group_dict.keys())
    group_names.sort()

    for group_name in group_names:
        temp_entry_no_dict = entry_group_dict[group_name]

        if 0 not in temp_entry_no_dict:
            danger('Wrongly processed dict for %s!' % group_name)
            sys.exit(1)

        known_bins = list(temp_entry_no_dict.keys())
        known_bins.sort()
        # max_bin = max(known_bins)
        max_bin = int(config['max_span']) * bucket_margin

        x_vals = []
        y_vals = []

        for bin_no in range(0, max_bin + 1):
            temp_bin_no = bin_no
            while temp_bin_no not in known_bins:
                temp_bin_no -= 1
            calibrated_bin_no = bin_no + 1
            x_vals.append(calibrated_bin_no)
            y_vals.append(temp_entry_no_dict[temp_bin_no])

        ax.plot(x_vals, y_vals, label=group_name)

        data_dict = {}
        for (i, x) in enumerate(x_vals):
            data_dict[x] = y_vals[i]

    edge_no_time_plot_filename = config['output_dir'] + '/' + "entry_no_over_time"
    ax.set(xlabel='time (%s)' % bucket, ylabel='entry no #',
           title='No of entries in queue over time')
    ax.grid()
    ax.legend()

    fig.savefig(edge_no_time_plot_filename)


def collect_entry_over_time(config, entry_group_dict, bucket_margin):

    # sort the group names, make sure every time the order is consistent
    group_names = list(entry_group_dict.keys())
    group_names.sort()

    for group_name in group_names:
        temp_entry_no_dict = entry_group_dict[group_name]

        if 0 not in temp_entry_no_dict:
            danger('Wrongly processed dict for %s!' % group_name)
            sys.exit(1)

        known_bins = list(temp_entry_no_dict.keys())
        known_bins.sort()
        # max_bin = max(known_bins)
        max_bin = int(config['max_span']) * bucket_margin

        x_vals = []
        y_vals = []

        for bin_no in range(0, max_bin + 1):
            temp_bin_no = bin_no
            while temp_bin_no not in known_bins:
                temp_bin_no -= 1
            calibrated_bin_no = bin_no + 1
            x_vals.append(calibrated_bin_no)
            y_vals.append(temp_entry_no_dict[temp_bin_no])

        data_dict = {}
        for (i, x) in enumerate(x_vals):
            data_dict[x] = y_vals[i]

        info("saving entry-time info for %s" % group_name)
        data_file_name = config['output_dir'] + '/' + group_name + '_entry_time.txt'
        with open(data_file_name, 'w') as fp:
            for (i, x) in enumerate(x_vals):
                fp.write('%d,%d\n' % (x, y_vals[i]))


@timed
def main():
    arg_parser = ArgParser(description='Analyze real path found over time.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the real path counter utility")

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

        # key: entry group name, value: entry_no_dict
        entry_group_dict = {}

        targets = config['targets']

        for target_name in targets:
            # key: bin_no, value: entry count
            entry_no_dict = {}
            target = targets[target_name]
            info("checking for %s" % target_name, 1)

            if not sanitize_target(target):
                danger("skipping invalid target", 1)
                continue

            entries = []
            entry_dirs = target['entry_dirs']
            # collect entry files first
            for entry_dir in entry_dirs:
                entry_files = os.listdir(entry_dir)

                for entry_file in entry_files:
                    # we only check the fuzzer output file
                    for pattern in config['entry_name_pattern']:
                        if re.fullmatch(pattern, entry_file) is not None:
                            entry_file = entry_dir + '/' + entry_file

                            entry_mtime = int(os.stat(entry_file).st_mtime)

                            # bin_no = int((entry_mtime - start_time) / self.bucket_margin)

                            entry = Entry(entry_file, entry_mtime, 0)

                            entries.append(entry)

                            break

            # sort the entry file list according to creation time
            entries.sort(key=lambda x: x.m_time, reverse=False)

            if target['start_time'] is None:
                start_time = entries[0].m_time
            else:
                start_time = int(target['start_time'])

            # update the bin_no after retrieving the start time
            for entry in entries:
                bin_no = int((entry.m_time - start_time) / bucket_margin)
                entry.bin_no = bin_no

            checked_entries = []

            # check each entry file
            for entry in entries:
                # info("checking %s -- %d" % (entry.path, entry.m_time), 1)
                temp_command = config['execute_command'].replace('@@', entry.path)
                if target['need_execution']:
                    proc = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    stdout, stderr = proc.communicate()
                else:
                    stdout = ''
                if config['false_path_pattern'] not in str(stdout):
                    checked_entries.append(entry)
                    entry_no_dict[entry.bin_no] = len(checked_entries)
            entry_group_dict[target_name] = entry_no_dict

        if bucket_margin == 3600:
            bucket_margin = 1
        elif bucket_margin == 1:
            bucket_margin = 3600

        if config['plot_figure']:
            plot_entry_over_time(config, entry_group_dict, bucket, bucket_margin, 1)

        collect_entry_over_time(config, entry_group_dict, bucket_margin)


if __name__ == "__main__":
    main()
