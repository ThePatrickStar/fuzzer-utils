import json
import os
import re
import sys
import argparse
from functools import reduce

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *


def sum_of_list(alist):
    return reduce(lambda x, y: x + y, alist)


def stats():
    arg_parser = argparse.ArgumentParser(description="Statistics of fot.")
    arg_parser.add_argument('-i', metavar='input', type=str, nargs="+",
                            help='path to input files.', required=True)
    arg_parser.add_argument('-o', metavar='output', type=str, required=True,
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
            warn("%s not exist, ingore." % filename)
        else:
            with open(filename, 'r') as f:
                # edge_cov_dict / func_cov_dict
                # { '5' : {rank0:(), rank1:(), ... },
                #   '10': {rank0:(), rank1:(), ... },
                #   '20': {rank0:(), rank1:(), ... }}
                # time_dict / total_bonus_dict / total_score_dict /
                # file_len_dict / edge_num_dict / func_num_dict
                # { '5' : {rank0:[], rank1:[], ... },
                #   '10': {rank0:[], rank1:[], ... },
                #   '20': {rank0:[], rank1:[], ... }}
                # rank_nums_dict
                # { '5' : {rank0:0.42, rank1:0.32, ... },
                #   '10': {rank0:0.42, rank1:0.32, ... },
                #   '20': {rank0:0.42, rank1:0.32, ... }}
                edge_cov_dict = {}
                func_cov_dict = {}
                simple_data_dict = {"time": {}, "total_bonus": {}, "total_score": {}, "file_len": {}, "edge_num": {},
                                    "func_num": {}}
                cycle_seq = 0
                for line in f.readlines():
                    if re.search("^cycle", line):
                        cycle_seq = line.split('-')[1].rstrip()
                        edge_cov_dict[cycle_seq] = dict()
                        func_cov_dict[cycle_seq] = dict()

                        for paramkey in simple_data_dict.keys():
                            simple_data_dict[paramkey][cycle_seq] = dict()
                    else:
                        # handle json here
                        single_testcase = json.loads(line)
                        rank = int(single_testcase["rank"])
                        edge_set = set(single_testcase["exec"]["deputy_trace"]["inner"])
                        func_set = set(single_testcase["exec"]["func_stats"]["covered_funcs"])
                        single_value_dict = {
                            "time": single_testcase["exec"]["us"],
                            "file_len": single_testcase["file"]["len"],
                            "total_bonus": single_testcase["exec"]["func_stats"]["total_bonus"],
                            "total_score": single_testcase["exec"]["func_stats"]["total_score"],
                            "edge_num": len(edge_set), "func_num": len(func_set)}

                        if rank in edge_cov_dict[cycle_seq]:
                            edge_cov_dict[cycle_seq][rank] |= edge_set
                            func_cov_dict[cycle_seq][rank] |= func_set

                            for paramkey in simple_data_dict.keys():
                                simple_data_dict[paramkey][cycle_seq][rank].append(single_value_dict[paramkey])
                        else:
                            edge_cov_dict[cycle_seq][rank] = edge_set
                            func_cov_dict[cycle_seq][rank] = func_set
                            for paramkey in simple_data_dict.keys():
                                simple_data_dict[paramkey][cycle_seq][rank] = [single_value_dict[paramkey]]

                # { 'edge': { 5 : {rank0: 0.41, rank1: 0.23, ...},
                #             10: {rank0: 0.43, rank1: 0.30, ...},
                #             20: {rank0: 0.48, rank1: 0.33, ...}},
                #
                #   'func': { 5 : {rank0: 0.41, rank1: 0.23, ...},
                #             10: {rank0: 0.43, rank1: 0.30, ...},
                #             20: {rank0: 0.48, rank1: 0.33, ...}},
                #
                #   'edge_num':  { 5:  {rank0: 50, rank1: 40, ... average:}
                #                  10: {rank0: 1235, rank1: 1010, ..., average:},
                #                  20: {rank0: 1293, rank1: 1002, ..., average:}},
                #
                #   'func_num':  { 5:  {rank0: 50, rank1: 40, ... average:}
                #                  10: {rank0: 1235, rank1: 1010, ..., average:},
                #                  20: {rank0: 1293, rank1: 1002, ..., average:}},
                #
                #   'time': { 5 : {rank0: 1234, rank1: 1010, ..., average:},
                #             10: {rank0: 1235, rank1: 1010, ..., average:},
                #             20: {rank0: 1293, rank1: 1002, ..., average:}},
                #
                #   'file_len':  { 5 : {rank0: 1234, rank1: 1010, ..., average:},
                #             10: {rank0: 1235, rank1: 1010, ..., average:},
                #             20: {rank0: 1293, rank1: 1002, ..., average:}},
                #
                #   'total_bonus': { 5 : {rank0: 1234, rank1: 1010, ..., average:},
                #                    10: {rank0: 1235, rank1: 1010, ..., average:},
                #                    20: {rank0: 1293, rank1: 1002, ..., average:}},
                #
                #   'total_score': { 5 : {rank0: 1234, rank1: 1010, ..., average:998 },
                #                    10: {rank0: 1035, rank1: 987, ..., average:788},
                #                    20: {rank0: 932, rank1: 901, ..., average:732}},
                #
                #   'rank_nums': { 5 : {rank0: 234, rank1: 110, ..., count:5999},
                #                  10: {rank0: 225, rank1: 107, ..., count:4792},
                #                  20: {rank0: 213, rank1: 102, ..., count:3991}}
                #
                # }
                result = {"edge": {}, "func": {}, "file_len": {}, "time": {}, "rank_nums": {}, "total_bonus": {},
                          "total_score": {}, "edge_num": {}, "func_num": {}}
                for key in edge_cov_dict:  # iterate over cycles

                    all_edges = set()
                    for e_set in edge_cov_dict[key].values():
                        all_edges |= e_set
                    count_edges = len(all_edges)
                    result["edge"][key] = dict(
                        (rank, round(len(e_set) / count_edges, 4)) for rank, e_set in edge_cov_dict[key].items())

                    all_funcs = set()
                    for f_set in func_cov_dict[key].values():
                        all_funcs |= f_set
                    count_funcs = len(all_funcs)
                    result["func"][key] = dict(
                        (rank, round(len(f_set) / count_funcs, 4)) for rank, f_set in func_cov_dict[key].items())

                    for paramkey in simple_data_dict.keys():
                        result[paramkey][key] = dict(
                            (rank, round(sum_of_list(list_of_a_rank) / len(list_of_a_rank))) for rank, list_of_a_rank in
                            simple_data_dict[paramkey][key].items())

                    result['rank_nums'][key] = dict((rank, len(timelist_of_a_rank)) for rank, timelist_of_a_rank in
                                                    simple_data_dict["time"][key].items())
                    result['rank_nums'][key]['count'] = sum_of_list(result['rank_nums'][key].values())

                    # add average
                    for paramkey in simple_data_dict.keys():
                        result[paramkey][key]["average"] = round(sum_of_list(
                            [result[paramkey][key][rank] * result["rank_nums"][key][rank] for rank in
                             result[paramkey][key]]) / result["rank_nums"][key]["count"])

                # write to files
                result_json_filename = args.o + '/' + os.path.splitext(os.path.basename(filename))[0] + '.json'
                with open(result_json_filename, 'w') as result_json_file:
                    json.dump(result, result_json_file)


if __name__ == "__main__":
    stats()
