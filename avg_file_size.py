import json
import os
import re
import shutil

from common_utils import *
from args import *
from edge_coverage.entry import *


def sanitize_config(config):
    required_params = ['targets', 'output_dir', 'entry_name_pattern']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    if len(config['targets']) == 0:
        danger("No target specified")
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

    return True


@timed
def main():
    arg_parser = ArgParser(description='Analyze average file size in folders.')
    required_args = arg_parser.add_argument_group('required arguments')
    required_args.add_argument('-c', help='Path to the configuration json file.', required=True)

    args = arg_parser.parse_args()

    info("Welcome to use the average file size checker utility")

    config_path = args.c

    with open(config_path) as config_file:
        config = json.load(config_file)
        if not sanitize_config(config):
            sys.exit(1)

        if os.path.isdir(config['output_dir']):
            warn("output dir %s exists, we will clear it this time" % config['output_dir'])
            shutil.rmtree(config['output_dir'])

        os.makedirs(config['output_dir'])

        targets = config['targets']

        for target_name in targets:

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

                            statinfo = os.stat(entry_file)

                            entry_mtime = int(statinfo.st_mtime)

                            entry = Entry(entry_file, entry_mtime, 0)

                            entry.size_in_bytes = int(statinfo.st_size)

                            entries.append(entry)

                            break

            # sort the entry file list according to creation time
            entries.sort(key=lambda x: x.size_in_bytes, reverse=False)

            total_size = 0
            total_no = len(entries)

            # update the bin_no after retrieving the start time
            for entry in entries:
                total_size += entry.size_in_bytes

            avg_size = float(total_size) / float(total_no)

            ok("Average file size for target {} is {} bytes.".format(target_name, avg_size))
            ok("Total file number for target {} is {}.".format(target_name, total_no))


if __name__ == "__main__":
    main()
