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
    required_params = ['output_dir', 'targets', 'entry_name_pattern', 'bucket']

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


def main():
    arg_parser = ArgParser(description='Analyze crash information (statistically & statically).')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the crash statistical analysis utility")

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

            entries = []

            # key: bin_no, value: count
            crash_no_dict = {}

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
                checked_entries.append(entry)
                # update the crash_no dict
                crash_no_dict[entry.bin_no] = len(checked_entries)
            if 0 not in crash_no_dict:
                crash_no_dict[0]=0
            entry_group_dict[group_name] = crash_no_dict

            ok("%s - Total number of unique crashes: %d" % (group_name, len(checked_entries)))

        # then we need to process the data and draw the plot
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # sort the group names, make sure every time the order is consistent
        group_names = list(entry_group_dict.keys())
        group_names.sort()

        for group_name in group_names:
            temp_crash_no_dict = entry_group_dict[group_name]

            if 0 not in temp_crash_no_dict:
                danger('Wrongly processed dict for %s!' % group_name)
                sys.exit(1)

            known_bins = list(temp_crash_no_dict.keys())
            known_bins.sort()

            # max_bin = max(known_bins)
            max_bin = int(config['max_span']) * bucket_margin

            x_vals = []
            y_vals = []

            for bin_no in range(0, max_bin+1):
                temp_bin_no = bin_no
                while temp_bin_no not in known_bins:
                    temp_bin_no -= 1
                calibrated_bin_no = bin_no + 1
                x_vals.append(calibrated_bin_no)
                y_vals.append(temp_crash_no_dict[temp_bin_no])

            ax.plot(x_vals, y_vals, label=group_name)

            info("saving crash-time info for %s" % group_name)
            data_file_name = config['output_dir'] + '/' + group_name + '_crash_time.txt'
            with open(data_file_name, 'w') as fp:
                for (i, x) in enumerate(x_vals):
                    fp.write('%d,%d\n' % (x, y_vals[i]))

        edge_no_time_plot_filename = config['output_dir'] + '/' + "crash_no_over_time"
        ax.set(xlabel='time (%s)' % bucket, ylabel='crash no #',
               title='No of unique crashes found over time')
        ax.grid()
        ax.legend()

        fig.savefig(edge_no_time_plot_filename)
        # plt.show()


if __name__ == "__main__":
    main()
