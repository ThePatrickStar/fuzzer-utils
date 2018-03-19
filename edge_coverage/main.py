import json
import os
import re
import shutil
import subprocess
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common_utils import *
from args import *


def sanitize_config(config):
    required_params = ['showmap_command', 'entry_dirs', 'showmap_output', 'output_dir', 'entry_name_pattern',
                       'start_time', 'bucket']

    valid_buckets = ['sec', 'min', 'hour', 's', 'm', 'h']

    for param in required_params:
        if param not in config:
            danger("%s is missing in the config file" % param)
            return False

    if len(config['entry_dirs']) == 0:
        danger("No entry directory specified")
        return False

    if config['bucket'].lower() not in valid_buckets:
        danger("Invalid bucket unit")
        return False

    # some amendments to config
    if not config['output_dir'].endswith('/'):
        config['output_dir'] += '/'

    return True


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

        base_command = config['showmap_command'].replace('##', config['showmap_output'])

        start_time = int(config['start_time'])

        covered_edges = set()

        for entry_dir in config['entry_dirs']:
            entry_files = os.listdir(entry_dir)

            for entry_file in entry_files:
                # we only check the fuzzer output file
                if re.fullmatch(config['entry_name_pattern'], entry_file) is not None:
                    entry_file = entry_dir + '/' + entry_file
                    info("checking %s" % entry_file)

                    temp_command = base_command.replace('@@', entry_file)
                    proc = subprocess.Popen(temp_command.split(' '), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                    proc.communicate()

                    with open(config['showmap_output']) as showmap_output_file:
                        lines = showmap_output_file.readlines()
                        for line in lines:
                            try:
                                edge_id = int(line.split(':')[0])
                                edge_count = int(line.split(':')[1])
                                covered_edges.add(edge_id)
                            except IndexError:
                                warn("cannot handle showmap output line: %s" % line, 1)

        ok("Total number of covered edges: %d" % len(covered_edges))


if __name__ == "__main__":
    main()
