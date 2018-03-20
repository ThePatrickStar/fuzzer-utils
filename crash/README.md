# Crash Statistical Analyzer

Plot the crash related information.

usage:

`python main.py -c config.json`

Explanation of the config file (we use regex here):

```
targets: essentially the output of each fuzzer
(requires 2 fields: entry_dirs, start_time) 

output_dir: the directory to put the plotted figures (outputs)

entry_name_pattern: the (regular expression) patterns for fuzzers' entry names 

start_time: the start time for the fuzzers (we assume every fuzzer starts at the same time; use time epoch here)

bucket: the time unit used to plot the "edge no over time".
(valid buckets are: "s", "m", "h", "sec", "min", "second", "minute", "hour", case does not matter)
```