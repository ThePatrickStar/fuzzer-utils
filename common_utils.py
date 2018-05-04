#!/usr/bin/env python3

from __future__ import print_function

import time


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
    print(indents + '\033[93m'+str(content)+'\033[0m')


@ascii_print
def ok(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[92m'+str(content)+'\033[0m')


@ascii_print
def info(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[94m'+str(content)+'\033[0m')


@ascii_print
def danger(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + '\033[91m'+str(content)+'\033[0m')


@ascii_print
def log(content, indent=0):
    indents = ''
    for i in range(0, indent):
        indents += '    '
    print(indents + str(content))
