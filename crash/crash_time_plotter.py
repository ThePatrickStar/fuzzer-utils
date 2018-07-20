import matplotlib.pyplot as plt
import os, sys, json
# TODO: deal with the dirty hack of importing
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common_utils import *
from args import *


def plot_crash_over_time(config, entry_group_dict, bucket, bucket_margin, fig_no, fname, title):
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

        ax.plot(x_vals, y_vals, label=group_name)

        data_dict = {}
        for (i, x) in enumerate(x_vals):
            data_dict[x] = y_vals[i]

    crash_no_time_plot_filename = config['output_dir'] + '/' + fname
    ax.set(xlabel='time (%s)' % bucket, ylabel='crash no #',
           title=title)
    ax.grid()
    ax.legend()

    fig.savefig(crash_no_time_plot_filename)
