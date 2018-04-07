import os, sys, json
# TODO: deal with the dirty hack of importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *
from args import *


def collect_crash_over_time(config, entry_group_dict, bucket_margin):

    # sort the group names, make sure every time the order is consistent
    group_names = list(entry_group_dict.keys())
    group_names.sort()

    for group_name in group_names:
        temp_entry_no_dict = entry_group_dict[group_name]

        if 0 not in temp_entry_no_dict:
            danger('Wrongly processed dict for %s!' % group_name)
            sys.exit(1)

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

        info("saving crash-time info for %s" % group_name)
        data_file_name = config['output_dir'] + '/' + group_name + '_crash_time.txt'
        with open(data_file_name, 'w') as fp:
            for (i, x) in enumerate(x_vals):
                fp.write('%d,%d\n' % (x, y_vals[i]))
