import threading
import sys
import os
import re
import subprocess

# TODO: deal with the dirty hack of importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *
from args import *
from entry import *


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


class Worker (threading.Thread):
    def __init__(self, tid, targets, config, bucket_margin):
        threading.Thread.__init__(self)
        self.tid = tid
        self.targets = targets
        self.edge_group_dict = {}
        self.entry_group_dict = {}
        self.config = config
        self.showmap_output = config['showmap_output']+'_'+str(tid)
        self.base_command = config['showmap_command'].replace('##', self.showmap_output)
        self.bucket_margin = bucket_margin

    def run(self):
        info("thread %d started" % self.tid)
        for target in self.targets:
            info("checking for %s" % target['name'], 1)
            if not sanitize_target(target):
                danger("skipping invalid target", 1)
                continue
            start_time = int(target['start_time'])
            group_name = target['name']
            entry_dirs = target['entry_dirs']

            covered_edges = set()

            entries = []

            # key: bin_no, value: edge count
            edge_no_dict = {}
            # key: bin_no, value: entry count
            entry_no_dict = {}

            # collect entry files first
            for entry_dir in entry_dirs:
                entry_files = os.listdir(entry_dir)

                for entry_file in entry_files:
                    # we only check the fuzzer output file
                    for pattern in self.config['entry_name_pattern']:
                        if re.fullmatch(pattern, entry_file) is not None:
                            entry_file = entry_dir + '/' + entry_file

                            entry_mtime = int(os.stat(entry_file).st_mtime)

                            bin_no = int((entry_mtime - start_time)/self.bucket_margin)

                            entry = Entry(entry_file, entry_mtime, bin_no)

                            entries.append(entry)

                            break

            # sort the entry file list according to creation time
            entries.sort(key=lambda x: x.m_time, reverse=False)

            checked_entries = []

            # check each entry file
            for entry in entries:
                # info("checking %s -- %d" % (entry.path, entry.m_time), 1)

                temp_command = self.base_command.replace('@@', entry.path)
                proc = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                proc.communicate()

                with open(self.showmap_output) as showmap_output_file:
                    lines = showmap_output_file.readlines()
                    for line in lines:
                        try:
                            edge_id = int(line.split(':')[0])
                            edge_count = int(line.split(':')[1])
                            covered_edges.add(edge_id)
                        except IndexError:
                            warn("cannot handle showmap output line: %s" % line, 1)

                # update the edge_no dict
                # NOTE: temporarily no difference
                checked_entries.append(entry)
                entry_no_dict[entry.bin_no] = len(checked_entries)

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
            ok("%s - Total number of covered edges: %d" % (group_name, len(covered_edges)), 1)
            ok("%s - Total number of entries: %d" % (group_name, len(checked_entries)), 1)