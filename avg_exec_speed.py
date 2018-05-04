#!/usr/bin/env python3
import os
import argparse
import glob
import re


def main():
    parser = argparse.ArgumentParser(description='avg_exec_speed: Calculate *average executions per second* for all tests in specified path (recusively)')
    parser.add_argument('path', metavar='path', type=str, nargs='+', help='the path containing *fuzzer_stats* files')
    parser.add_argument('--no-path',action='store_true', help='show value only, supress path')

    args = parser.parse_args()
    for path in args.path:
        if os.path.isdir(path):
            for stats_file in sorted(glob.glob(path+'/**/fuzzer_stats', recursive=True)):
                start_time, last_update, execs_done = [0,1,-1]
                with open(stats_file, 'r') as statsfile:
                    for line in statsfile.readlines():
                        hit_count = 0
                        if re.search('^start_time', line):
                            start_time = int(line.split()[2])
                            hit_count += 1
                        elif re.search('^last_update', line):
                            last_update = int(line.split()[2])
                            hit_count += 1
                        elif re.search('^execs_done', line):
                            execs_done = int(line.split()[2])
                            hit_count += 1
                            if hit_count == 3:
                                break
                if args.no_path:
                    print(round(execs_done / (last_update-start_time)))
                else:
                    print(os.path.abspath(stats_file), ': ', round(execs_done / (last_update-start_time)))
        else:
            print("warning: %s is not a path and is skipped" % path)


if __name__ == "__main__":
    main()
