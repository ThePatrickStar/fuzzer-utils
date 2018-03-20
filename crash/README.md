# Crash Statistical Analyzer

Plot the crash related information.

usage:

`python main.py -c config.json`

Explanation of the config file (we use regex here):

```
entry_dirs_.+ : the entry directories (queues of fuzzers).
(The script will automatically group the results of one of these params as one plot.
For example, we can have entry_dirs_afl and entry_dirs_fot, and we will end up with 2 plots per fig.)

output_dir: the directory to put the plotted figures (outputs)

entry_name_pattern: the (regular expression) patterns for fuzzers' entry names 

start_time: the start time for the fuzzers (we assume every fuzzer starts at the same time; use time epoch here)

bucket: the time unit used to plot the "edge no over time".
(valid buckets are: "s", "m", "h", "sec", "min", "second", "minute", "hour", case does not matter)
```