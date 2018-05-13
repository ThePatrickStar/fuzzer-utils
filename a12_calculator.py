import argparse
import json

from common_utils import *


def sanitize_ff_times(max_pop, max_val, report_name, report_key, ff_times):
    if len(ff_times) > max_pop:
        danger("Actual first find times larger than max pop in %s: %s" % (report_name, report_key))
        exit(1)
    # fill up the missing population with max val
    while len(ff_times) < max_pop:
        ff_times.append(max_val)
    ff_times.sort()
    return ff_times


def calculate_statistics(report_1, report_2, compared_keys, max_pop, max_val, first_name, second_name):
    for report_key in report_1:
        if report_key in compared_keys:
            continue
        compared_keys.append(report_key)
        first_ff_times = [x[1] for x in report_1[report_key]["ff_times"]]

        first_ff_times = sanitize_ff_times(max_pop, max_val, first_name, report_key, first_ff_times)

        if report_key not in report_2:
            second_ff_times = [max_val] * max_pop
        else:
            second_ff_times = [x[1] for x in report_2[report_key]["ff_times"]]
            second_ff_times = sanitize_ff_times(max_pop, max_val, second_name, report_key, second_ff_times)

        # log(first_ff_times)
        # info(second_ff_times)

        # calculate the actual a12 (1<=2) and a21 (2<=1) values
        numerator = 0
        denominator = float(max_pop * max_pop)
        for first_val in first_ff_times:
            for second_val in second_ff_times:
                if first_val < second_val:
                    numerator += 1
                elif first_val == second_val:
                    numerator += 0.5
        a12 = numerator / denominator

        # just for validation purpose
        # numerator = 0
        # denominator = float(max_pop * max_pop)
        # for first_val in first_ff_times:
        #     for second_val in second_ff_times:
        #         if first_val > second_val:
        #             numerator += 1
        #         elif first_val == second_val:
        #             numerator += 0.5
        # a21 = numerator / denominator
        a21 = 1 - a12

        info("=== KEY: %s ===" % report_key)
        log("%s <= %s is %.2f" % (first_name, second_name, a12), 1)
        log("%s >= %s is %.2f" % (first_name, second_name, a21), 1)

    return compared_keys


def main():
    parser = argparse.ArgumentParser(description='calculate the Vargha-Delaney statistic (A_{12})')
    parser.add_argument('first', metavar='first', type=str, help='the first report')
    parser.add_argument('second', metavar='second', type=str, help='the second report')
    parser.add_argument('--max-pop', default=8, help='maximum population (runs)')
    parser.add_argument('--max-val', default=14400, help='maximum value to fill up')

    args = parser.parse_args()

    first_report_file = open(args.first)
    second_report_file = open(args.second)
    max_pop = args.max_pop
    max_val = args.max_val
    compared_keys = []

    first_report = json.load(first_report_file)
    second_report = json.load(second_report_file)

    compared_keys = calculate_statistics(first_report, second_report, compared_keys, max_pop, max_val, args.first, args.second)
    calculate_statistics(second_report, first_report, compared_keys, max_pop, max_val, args.second, args.first)

    first_report_file.close()
    second_report_file.close()


if __name__ == "__main__":
    main()
