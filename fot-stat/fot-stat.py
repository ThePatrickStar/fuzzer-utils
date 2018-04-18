import json
import os
import re
import sys
import argparse
from functools import reduce

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *


def avg_stats():
    pass


def stats():
    arg_parser = argparse.ArgumentParser(description="Statistics of fot.")
    arg_parser.add_argument('-i', metavar='input',  type=str, nargs="+",
                            help='path to input files.', required=True)
    arg_parser.add_argument('-o', metavar='ouput',  type=str, required=True,
                            help='path to directory containing output files.')
    args = arg_parser.parse_args()

    if os.path.exists(args.o):
        if os.path.isfile(args.o):
            warn("%s is an existing file. Abort" % args.o)
            exit(1)
        if os.listdir(args.o):
            warn(" %s exists and is not empty. Abort." % args.o)
            exit(1)
    else:
        os.makedirs(args.o)

    input_list = [os.path.basename(filename) for filename in args.i]
    if len(set(input_list)) < len(input_list):
        warn("Currently the script does not support multiple input files \
             sharing common basename, because it names output files \
             according to basename. Abort")
        exit(2)

    for filename in args.i:
        if not os.path.isfile(filename):
            warn("%s not exist, ingore." % path)
        else:
            with open(filename, 'r') as f:
                # block_cov_dict / func_cov_dict
                # { '5' : {rank1:(), rank2:(), ... },
                #   '10': {rank1:(), rank2:(), ... },
                #   '20': {rank1:(), rank2:(), ... }}
                # time_dict
                # { '5' : {rank1:[], rank2:[], ... },
                #   '10': {rank1:[], rank2:[], ... },
                #   '20': {rank1:[], rank2:[], ... }}
                block_cov_dict = {}
                func_cov_dict = {}
                time_dict = {}
                cycle_seq = 0
                for line in f.readlines():
                    if re.search("^cycle", line):
                        cycle_seq = line.split('-')[1].rstrip()
                        block_cov_dict[cycle_seq] = dict()
                        func_cov_dict[cycle_seq] = dict()
                        time_dict[cycle_seq] = dict()
                    else:
                        # line = json.loads(line)
                        # handle json here
                        single_testcase = json.loads(line)
                        rank = single_testcase["rank"] # rank: integer, used as index of list
                        block_set = set(single_testcase["exec"]["deputy_trace"]["inner"])
                        func_set = set(single_testcase["exec"]["func_stats"]["covered_funcs"])
                        time_us = single_testcase["exec"]["us"]

                        if rank in block_cov_dict[cycle_seq] :
                             block_cov_dict[cycle_seq][rank]|=(block_set)
                             func_cov_dict[cycle_seq][rank]|=(func_set)
                             time_dict[cycle_seq][rank].append(time_us)
                        else:
                            block_cov_dict[cycle_seq][rank] = block_set
                            func_cov_dict[cycle_seq][rank]=func_set
                            time_dict[cycle_seq][rank] = [time_us]

                # { 'block': { 5 : {rank1: 0.41, rank2: 0.23, ...},
                #              10: {rank1: 0.43, rank2: 0.30, ...},
                #              20: {rank1: 0.48, rank2: 0.33, ...}},
                #
                #   'func' : { 5 : {rank1: 0.41, rank2: 0.23, ...},
                #              10: {rank1: 0.43, rank2: 0.30, ...},
                #              20: {rank1: 0.48, rank2: 0.33, ...}},
                #
                #   'time' : { 5 : {rank1: 1234, rank2: 1010, ...},
                #              10: {rank1: 1235, rank2: 1010, ...},
                #              20: {rank1: 1293, rank2: 1002, ...}}
                # }
                result={"block": {}, "func":{}, "time":{}}
                count_blocks = count_funcs = 0
                for key in block_cov_dict: # iterate over cycle

                    all_blocks=set()
                    for b_set in block_cov_dict[key].values():
                        all_blocks |= b_set
                    count_blocks = len(all_blocks)
                    result["block"][key] = dict((rank,round(len(b_set)/count_blocks,4)) for rank, b_set in block_cov_dict[key].items())

                    all_funcs=set()
                    for f_set in func_cov_dict[key].values():
                        all_funcs |= f_set
                    count_funcs = len(all_funcs)
                    result["func"][key] = dict((rank, round(len(f_set)/count_funcs,4)) for rank, f_set in func_cov_dict[key].items())

                    result['time'][key] = dict((rank, round(reduce(lambda x, y:x+y, timelist_of_a_rank)/len(timelist_of_a_rank))) for rank, timelist_of_a_rank in time_dict[key].items())

                # write to files
                result_json_filename = args.o + '/' + os.path.splitext(os.path.basename(filename))[0] + '.json'
                with open (result_json_filename, 'w') as result_json_file:
                    json.dump(result, result_json_file)


if __name__ == "__main__":
    stats()
