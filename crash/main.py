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
from crash_time_plotter import *
from data_collector import *
from edge_coverage.worker import get_bucket
# from edge_coverage.worker import sanitize_target


def inspect_bitmap(bitmap_file, hit_count_bucket, hit_count_alt, covered_edges):
    is_new_path = False
    is_new_path_alt = False
    with open(bitmap_file) as bitmap_f:
        for line in bitmap_f.readlines():
            try:
                edge_id = int(line.split(':')[0])
                edge_count_alt = int(line.split(':')[1])
                edge_count = get_bucket(edge_count_alt)  # with bucket

                if edge_id not in hit_count_bucket:
                    hit_count_bucket[edge_id] = [edge_count]
                    is_new_path = True
                else:
                    if edge_count not in hit_count_bucket[edge_id]:
                        is_new_path = True
                        hit_count_bucket[edge_id].append(edge_count)
                if edge_id not in hit_count_alt:
                    hit_count_alt[edge_id] = [edge_count_alt]
                    is_new_path_alt = True
                else:
                    if edge_count_alt not in hit_count_alt[edge_id]:
                        is_new_path_alt = True
                        hit_count_alt[edge_id].append(edge_count_alt)

                covered_edges.add(edge_id)
            except IndexError:
                warn("cannot handle showmap output line: %s" % line, 1)
    return [is_new_path, is_new_path_alt]


def sanitize_config(config):
    required_params = ['showmap_command', 'output_dir', 'targets', 'entry_name_pattern', 'bucket']

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
            group_name = target_key

            # collect entry files first
            entries = []
            for entry_dir in target['entry_dirs']:
                for entry_file in os.listdir(entry_dir):
                    # we only check the fuzzer output file
                    for pattern in config['entry_name_pattern']:
                        if re.fullmatch(pattern, entry_file) is not None:
                            entry_file = entry_dir + '/' + entry_file
                            entry_mtime = int(os.stat(entry_file).st_mtime)
                            bin_no = 0
                            entries.append(Entry(entry_file, entry_mtime, bin_no))
                            break

            # sort the entry file list according to creation time
            entries.sort(key=lambda x: x.m_time, reverse=False)

            # assign earliest m_time to start_time if it is none in sanitize_target()
            if target['start_time'] is None:
                start_time = entries[0].m_time
            else:
                start_time = int(target['start_time'])

            checked_entries = []
            new_paths = []
            new_paths_alt = []
            covered_edges = set()

            # key: edge_id, value: hitcounts (bucket)
            hitcount_dict = {}
            # key: edge_id, value: hitcounts (no bucket)
            hitcount_dict_alt = {}
            # key: bin_no, value: count
            crash_no_dict = {}
            # key: bin_no, value: entry count
            entry_no_dict = {}
            # key: bin_no, value: entry count (no bucket)
            entry_no_dict_alt = {}
            map_file = config['showmap_output'] + '_crash'
            base_command = config['showmap_command'].replace('##', map_file)
            # check each entry file
            for entry in entries:
                entry.bin_no = int((entry.m_time - start_time) / bucket_margin)
                temp_command = base_command.replace('@@', entry.path)
                run_showmap = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                run_showmap.communicate()
                # TODO: handle stderr/stdout to get signal
                is_new_path, is_new_path_alt = inspect_bitmap(map_file, hitcount_dict, hitcount_dict_alt, covered_edges)
                checked_entries.append(entry)
                if is_new_path:
                    new_paths.append(entry)
                if is_new_path_alt:
                    new_paths_alt.append(entry)
                entry_no_dict[entry.bin_no] = len(new_paths)
                entry_no_dict_alt[entry.bin_no] = len(new_paths_alt)

                # update the crash_no dict
                crash_no_dict[entry.bin_no] = len(covered_edges)

            if 0 not in crash_no_dict:
                crash_no_dict[0] = 0
            if 0 not in entry_no_dict:
                entry_no_dict[0] = 0
            entry_group_dict[group_name] = crash_no_dict

            ok("%s - Total number of unique crashes: %d" % (group_name, len(checked_entries)))

        if bucket_margin == 3600:
            bucket_margin = 1
        elif bucket_margin == 1:
            bucket_margin = 3600

        if config['plot_figure']:
            plot_crash_over_time(config, entry_group_dict, bucket, bucket_margin, 1)

        collect_crash_over_time(config, entry_group_dict, bucket_margin)


if __name__ == "__main__":
    main()
