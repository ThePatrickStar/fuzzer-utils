#!/usr/bin/env python3

import json
import os
import re
import subprocess
import shutil
import sys
import matplotlib.pyplot as plt

from common_utils import *
from args import *


class Patch:
    path = ''
    m_time = 0
    bin_no = 0

    def __init__(self, path, m_time, bin_no):
        self.path = path
        self.m_time = m_time
        self.bin_no = bin_no


def sanitize_config(config):
    required_params = ['exec_cmd', 'targets', 'bucket', 'output_file', 'crash_name_pattern']

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
    required_params = ['crash_dirs']

    for param in required_params:
        if param not in target:
            danger("%s is missing in target")
            return False

    if len(target['crash_dirs']) == 0:
        danger('No entry dir specified for target')
        return False

    else:
        # fuzzy finding
        fuzzy_stats_loc = ['/../fuzzer_stats', '/fuzzer_stats']
        stats_file_found = False
        stats_file = None
        for entry_dir in target['crash_dirs']:
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


@timed
def main():
    arg_parser = ArgParser(description='Analyze patch hits.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)
    # arg_parser.add_argument('-v', help="Verbose", required=False)

    args = arg_parser.parse_args()

    info("Welcome to use the patch hit analysis utility")

    config_path = args.c

    with open(config_path) as config_file:
        config = json.load(config_file)
        if not sanitize_config(config):
            sys.exit(1)

        targets = config['targets']
        exec_cmd = config['exec_cmd']

        # default bucket margin is one hour
        bucket_margin = 3600
        bucket = config['bucket']
        if bucket.lower() in ['minute', 'min', 'm']:
            bucket_margin = 60
        elif bucket.lower() in ['second', 'sec', 's']:
            bucket_margin = 1

        if os.path.isfile(config['output_file']):
            warn("output file %s exists, we will clear it this time" % config['output_file'])
            os.remove(config['output_file'])

        # key: trace; value: trace related info {find_runs: ..., times: ..., avg_time: ...}
        trace_crash_dict = {}

        for target_name in targets:
            target = targets[target_name]
            sanitize_target(target)
            crash_dirs = target['crash_dirs']
            start_time = target['start_time']
            found_traces = []

            for crash_dir in crash_dirs:
                crash_files = os.listdir(crash_dir)
                crash_files.sort()

                for crash_file in crash_files:
                    # we only check the fuzzer output file
                    for pattern in config['crash_name_pattern']:
                        if re.fullmatch(pattern, crash_file) is not None:
                            crash_file = crash_dir + '/' + crash_file

                            crash_mtime = int(os.stat(crash_file).st_mtime)

                            bin_no = int((crash_mtime - start_time) / bucket_margin)

                            tmp_cmd = exec_cmd.replace('@@', crash_file)

                            proc = subprocess.Popen(tmp_cmd.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                            stdout, stderr = proc.communicate()

                            rc = proc.returncode

                            # if stack_trace is None:
                            #     stack_trace = get_stack_trace(stdout)

                            if rc not in found_traces and rc is not None:
                                found_traces.append(rc)
                                if rc not in trace_crash_dict:
                                    trace_crash_dict[rc] = {'find_runs': 1, 'ff_times': [(crash_file, bin_no)]}
                                else:
                                    trace_crash_dict[rc]['find_runs'] += 1
                                    trace_crash_dict[rc]['ff_times'].append((crash_file, bin_no))

            # update the mean time to discover for each trace
            for trace_name in trace_crash_dict:
                trace_info = trace_crash_dict[trace_name]
                avg_time = float(sum([pair[1] for pair in trace_info['ff_times']]))/float(len(trace_info['ff_times']))
                trace_info['avg_time'] = avg_time

            # generate the output file
            output_file = config['output_file']
            with open(output_file, 'w') as fd:
                pp = json.dumps(trace_crash_dict, indent=4, sort_keys=True)
                fd.write(pp)


if __name__ == "__main__":
    main()
