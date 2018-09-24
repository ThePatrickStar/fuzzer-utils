from __future__ import print_function
import argparse
import json
import os
import re
import shutil
import threading
import sys
import subprocess
import matplotlib.pyplot as plt
import time


######### previously args

class ArgParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


######### previously common_utils

def ascii_print(func):
    def print_wrapper(content, indent=0):
        try:
            func(content, indent=indent)
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            danger(e)

    return print_wrapper


def timed(func):
    def time_wrapper(**kwargs):
        start_time = time.time()
        func(**kwargs)
        end_time = time.time()
        info("function %s takes %fs to execute" % (func.__name__, (end_time - start_time)))

    return time_wrapper


@ascii_print
def warn(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[93m' + "[Warning] " + str(content) + '\033[0m')


@ascii_print
def ok(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[92m' + str(content) + '\033[0m')


@ascii_print
def info(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[94m' + str(content) + '\033[0m')


@ascii_print
def danger(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[91m' + "[Danger] " + str(content) + '\033[0m')


@ascii_print
def log(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + str(content))

######### previously data_collector

def collect_entry_over_time(config, entry_group_dict, bucket_margin, fname):

    # sort the group names, make sure every time the order is consistent
    group_names = list(entry_group_dict.keys())
    group_names.sort()

    for group_name in group_names:
        temp_entry_no_dict = entry_group_dict[group_name]

        if 0 not in temp_entry_no_dict:
            danger('Wrongly processed dict for %s!' % group_name)
            s_p = min([n for n in temp_entry_no_dict if int(n) > 0])
            temp_entry_no_dict[0] = temp_entry_no_dict[s_p]
            # sys.exit(1)

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

        data_file_name = config['output_dir'] + '/' + group_name + fname
        info("saving entry-time info for {0} into {1}".format(group_name, data_file_name))
        with open(data_file_name, 'w') as fp:
            for (i, x) in enumerate(x_vals):
                fp.write('%d,%d\n' % (x, y_vals[i]))


def collect_edge_over_time(config, edge_group_dict, bucket_margin, fname, remove_init_edges=False, init_edges=0):

    # sort the group names, make sure every time the order is consistent
    group_names = list(edge_group_dict.keys())
    group_names.sort()

    for group_name in group_names:
        temp_edge_no_dict = edge_group_dict[group_name]

        if 0 not in temp_edge_no_dict:
            danger('Wrongly processed dict for %s!' % group_name)
            s_p = min([n for n in temp_edge_no_dict if int(n) > 0])
            temp_edge_no_dict[0] = temp_edge_no_dict[s_p]
            # sys.exit(1)

        known_bins = list(temp_edge_no_dict.keys())
        known_bins.sort()
        # max_bin = max(known_bins)
        max_bin = int(config['max_span']) * bucket_margin

        x_vals = []
        y_vals = []

        # log("known bins are %s" % str(known_bins))
        # log("max_bin is %d" % max_bin)
        for bin_no in range(0, max_bin + 1):
            temp_bin_no = bin_no
            while temp_bin_no not in known_bins:
                temp_bin_no -= 1
            calibrated_bin_no = bin_no + 1
            x_vals.append(calibrated_bin_no)
            if remove_init_edges:
                y_vals.append(temp_edge_no_dict[temp_bin_no] - init_edges)
            else:
                y_vals.append(temp_edge_no_dict[temp_bin_no])

        info("saving edge-time info for %s" % group_name)
        data_file_name = config['output_dir'] + '/' + group_name + fname
        with open(data_file_name, 'w') as fp:
            for (i, x) in enumerate(x_vals):
                fp.write('%d,%d\n' % (x, y_vals[i]))

######### previously entry_time_plotter

def plot_entry_over_time(config, entry_group_dict, bucket, bucket_margin, fig_no, fname, title):
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
            s_p = min([n for n in temp_entry_no_dict if int(n) > 0])
            temp_entry_no_dict[0] = temp_entry_no_dict[s_p]
            # sys.exit(1)

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

    edge_no_time_plot_filename = config['output_dir'] + '/' + fname
    ax.set(xlabel='time (%s)' % bucket, ylabel='entry no #',
           title=title)
    ax.grid()
    ax.legend()

    fig.savefig(edge_no_time_plot_filename)

######### previously edge_time_plotter

def plot_edge_over_time(config, edge_group_dict, bucket, bucket_margin, fig_no, fname, title, remove_init_edges=False,
                        init_edges=0):
    # then we need to process the data and draw the plot
    fig = plt.figure(fig_no)
    ax = fig.add_subplot(111)

    # sort the group names, make sure every time the order is consistent
    group_names = list(edge_group_dict.keys())
    group_names.sort()

    for group_name in group_names:
        temp_edge_no_dict = edge_group_dict[group_name]

        if 0 not in temp_edge_no_dict:
            danger('Wrongly processed dict for %s!' % group_name)
            s_p = min([n for n in temp_edge_no_dict if int(n) > 0])
            temp_edge_no_dict[0] = temp_edge_no_dict[s_p]
            # sys.exit(1)

        known_bins = list(temp_edge_no_dict.keys())
        known_bins.sort()
        # max_bin = max(known_bins)
        max_bin = int(config['max_span']) * bucket_margin

        x_vals = []
        y_vals = []

        # log("known bins are %s" % str(known_bins))
        # log("max_bin is %d" % max_bin)
        for bin_no in range(0, max_bin + 1):
            temp_bin_no = bin_no
            while temp_bin_no not in known_bins:
                temp_bin_no -= 1
            calibrated_bin_no = bin_no + 1
            x_vals.append(calibrated_bin_no)
            if remove_init_edges:
                y_vals.append(temp_edge_no_dict[temp_bin_no] - init_edges)
            else:
                y_vals.append(temp_edge_no_dict[temp_bin_no])

        ax.plot(x_vals, y_vals, label=group_name)

    edge_no_time_plot_filename = config['output_dir'] + '/' + fname
    ax.set(xlabel='time (%s)' % bucket, ylabel='edge no #',
           title=title)
    ax.grid()
    ax.legend()

    fig.savefig(edge_no_time_plot_filename)

######### previously worker

class Entry:
    path = ''
    m_time = 0
    bin_no = 0
    size_in_bytes = 0

    def __init__(self, path, m_time, bin_no):
        self.path = path
        self.m_time = m_time
        self.bin_no = bin_no

######### previously worker


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


def get_bucket(hitcount):
    if hitcount <= 4:
        return hitcount
    elif hitcount < 8:
        return 4
    elif hitcount < 16:
        return 8
    elif hitcount < 32:
        return 16
    elif hitcount < 128:
        return 32
    else:
        return 128


class Worker(threading.Thread):
    def __init__(self, tid, targets, config, bucket_margin):
        threading.Thread.__init__(self)
        self.tid = tid
        self.targets = targets
        self.edge_group_dict = {}
        self.entry_group_dict = {}
        self.entry_group_dict_alt = {}
        self.config = config
        self.showmap_output = config['showmap_output'] + '_' + str(tid)
        self.base_command = config['showmap_command'].replace('##', self.showmap_output)
        self.bucket_margin = bucket_margin

    def run(self):
        info("thread %d started" % self.tid)
        for target in self.targets:
            info("checking for %s" % target['name'], 1)
            if not sanitize_target(target):
                danger("skipping invalid target", 1)
                continue

            bin_limit = (3600/self.bucket_margin) * int(self.config['max_span'])
            entries = []
            entry_dirs = target['entry_dirs']
            # collect entry files first
            for entry_dir in entry_dirs:
                entry_files = os.listdir(entry_dir)

                for entry_file in entry_files:
                    # we only check the fuzzer output file
                    for pattern in self.config['entry_name_pattern']:
                        if re.fullmatch(pattern, entry_file) is not None:
                            entry_file = entry_dir + '/' + entry_file

                            entry_mtime = int(os.stat(entry_file).st_mtime)

                            # bin_no = int((entry_mtime - start_time) / self.bucket_margin)

                            entry = Entry(entry_file, entry_mtime, 0)

                            if entry.bin_no > bin_limit:
                                continue

                            entries.append(entry)

                            break

            # sort the entry file list according to creation time
            entries.sort(key=lambda x: x.m_time, reverse=False)

            if target['start_time'] is None:
                start_time = entries[0].m_time
            else:
                start_time = int(target['start_time'])
            group_name = target['name']

            covered_edges = set()

            # key: edge_id, value: hitcounts (bucket)
            hitcount_dict = {}
            # key: edge_id, value: hitcounts (no bucket)
            hitcount_dict_alt = {}

            # key: bin_no, value: edge count
            edge_no_dict = {}
            # key: bin_no, value: entry count
            entry_no_dict = {}
            # key: bin_no, value: entry count (no bucket)
            entry_no_dict_alt = {}

            # update the bin_no after retrieving the start time
            for entry in entries:
                bin_no = int((entry.m_time - start_time) / self.bucket_margin)
                entry.bin_no = bin_no

            checked_entries = []

            new_paths = []
            new_paths_alt = []

            # check each entry file
            for entry in entries:
                # info("checking %s -- %d" % (entry.path, entry.m_time), 1)

                temp_command = self.base_command.replace('@@', entry.path)
                proc = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                proc.communicate()

                is_new_path = False
                is_new_path_alt = False

                with open(self.showmap_output) as showmap_output_file:
                    lines = showmap_output_file.readlines()
                    for line in lines:
                        try:
                            edge_id = int(line.split(':')[0])
                            edge_count_alt = int(line.split(':')[1])
                            edge_count = get_bucket(edge_count_alt)

                            if edge_id not in hitcount_dict:
                                hitcount_dict[edge_id] = [edge_count]
                                is_new_path = True
                            else:
                                if edge_count not in hitcount_dict[edge_id]:
                                    is_new_path = True
                                    hitcount_dict[edge_id].append(edge_count)
                            if edge_id not in hitcount_dict_alt:
                                hitcount_dict_alt[edge_id] = [edge_count_alt]
                                is_new_path_alt = True
                            else:
                                if edge_count_alt not in hitcount_dict_alt[edge_id]:
                                    is_new_path_alt = True
                                    hitcount_dict_alt[edge_id].append(edge_count_alt)

                            covered_edges.add(edge_id)
                        except IndexError:
                            warn("cannot handle showmap output line: %s" % line, 1)

                checked_entries.append(entry)
                if is_new_path:
                    new_paths.append(entry)
                if is_new_path_alt:
                    new_paths_alt.append(entry)

                entry_no_dict[entry.bin_no] = len(new_paths)

                entry_no_dict_alt[entry.bin_no] = len(new_paths_alt)

                # update the edge_no dict
                # NOTE: temporarily no difference
                if entry.bin_no not in edge_no_dict:
                    edge_no_dict[entry.bin_no] = len(covered_edges)
                else:
                    edge_no_dict[entry.bin_no] = len(covered_edges)

            if 0 not in edge_no_dict:
                edge_no_dict[0] = 0
            if 0 not in entry_no_dict:
                entry_no_dict[0] = 0

            self.edge_group_dict[group_name] = edge_no_dict
            self.entry_group_dict[group_name] = entry_no_dict
            self.entry_group_dict_alt[group_name] = entry_no_dict_alt
            ok("%s - Total number of covered edges: %d" % (group_name, len(covered_edges)), 1)
            ok("%s - Total number of entries: %d" % (group_name, len(checked_entries)), 1)
            ok("%s - Total number of real paths: %d" % (group_name, len(new_paths)), 1)
            ok("%s - Total number of real paths (no bucket): %d" % (group_name, len(new_paths_alt)), 1)



######### previously main


def sanitize_config(config):
    required_params = ['showmap_command', 'targets', 'showmap_output', 'output_dir', 'entry_name_pattern', 'bucket']

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


@timed
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

        # default bucket margin is one hour
        bucket_margin = 3600
        bucket = config['bucket']
        if bucket.lower() in ['minute', 'min', 'm']:
            bucket_margin = 60
        elif bucket.lower() in ['second', 'sec', 's']:
            bucket_margin = 1

        # key: entry group name, value: edge_no_dict
        edge_group_dict = {}
        # key: entry group name, value: entry_no_dict
        entry_group_dict = {}
        # key: entry group name, value: entry_no_dict_alt
        entry_group_dict_alt = {}

        targets = config['targets']

        workers = []

        # temporarily create a worker for every target
        for (i, target_key) in enumerate(targets.keys()):
            # info("checking for %s" % target_key)
            target = targets[target_key]
            target['name'] = target_key
            worker = Worker(i, [target], config, bucket_margin)
            workers.append(worker)

        ok("starting %d workers" % len(workers))
        for worker in workers:
            worker.start()

        remove_init_info = False
        init_edges = 0
        init_seeds = 0
        init_entries = []
        # optionally remove init seeds info
        if 'init_seeds_dir' in config:
            remove_init_info = True
            init_files = os.listdir(config['init_seeds_dir'])
            init_seeds = len(init_files)

            for init_file in init_files:
                init_file = config['init_seeds_dir'] + '/' + init_file

                entry_mtime = int(os.stat(init_file).st_mtime)

                # bin_no = int((entry_mtime - start_time) / self.bucket_margin)

                entry = Entry(init_file, entry_mtime, 0)

                init_entries.append(entry)

            init_entries.sort(key=lambda x: x.m_time, reverse=False)

            covered_edges = set()
            showmap_output = config['showmap_output'] + '_main'
            base_command = config['showmap_command'].replace('##', showmap_output)

            for entry in init_entries:
                # info("checking %s -- %d" % (entry.path, entry.m_time), 1)

                temp_command = base_command.replace('@@', entry.path)
                proc = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                proc.communicate()

                with open(showmap_output) as showmap_output_file:
                    lines = showmap_output_file.readlines()
                    for line in lines:
                        try:
                            edge_id = int(line.split(':')[0])
                            covered_edges.add(edge_id)
                        except IndexError:
                            warn("cannot handle showmap output line: %s" % line, 1)
            init_edges = len(covered_edges)

            info('{} initial seeds covered {} edges'.format(init_seeds, init_edges))

        for worker in workers:
            worker.join()
        for worker in workers:
            for group in worker.edge_group_dict:
                edge_group_dict[group] = worker.edge_group_dict[group]
            for group in worker.entry_group_dict:
                entry_group_dict[group] = worker.entry_group_dict[group]
            for group in worker.entry_group_dict_alt:
                entry_group_dict_alt[group] = worker.entry_group_dict_alt[group]

        if bucket_margin == 3600:
            bucket_margin = 1
        elif bucket_margin == 1:
            bucket_margin = 3600

        if config['plot_figure']:
            plot_edge_over_time(config, edge_group_dict, bucket, bucket_margin, 1, "edge_no_over_time", 'No of edges covered over time')
            plot_entry_over_time(config, entry_group_dict, bucket, bucket_margin, 2, "entry_no_over_time_bucket", 'No of entries in queue over time (bucket)')
            plot_entry_over_time(config, entry_group_dict_alt, bucket, bucket_margin, 3, "entry_no_over_time", 'No of entries in queue over time')
            if remove_init_info:
                plot_edge_over_time(config, edge_group_dict, bucket, bucket_margin, 4, "edges_found_time", 'No of edges discovered over time', True, init_edges)

        collect_entry_over_time(config, entry_group_dict, bucket_margin, '_entry_time_bucket.txt')
        collect_entry_over_time(config, entry_group_dict_alt, bucket_margin, '_entry_time.txt')
        collect_edge_over_time(config, edge_group_dict, bucket_margin, '_edge_time.txt')
        if remove_init_info:
            collect_edge_over_time(config, edge_group_dict, bucket_margin, '_edge_time_found.txt', True, init_edges)


if __name__ == "__main__":
    main()
