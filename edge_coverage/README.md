# Edge Coverage Analyzer

Plot the edge coverage related information.

usage:

`python main.py -c config.json`

Explanation of the config file (we use regex here):

```
showmap_command : the command to run afl-showmap
(use ## as the placeholder for the showmap output file, 
use @@ as the placeholder for the input file of the target program)

targets: essentially the output of each fuzzer
(requires 2 fields: entry_dirs, start_time)

showmap_output: the temporary file used for afl-showmap (to replace the "##" in showmap_command)

output_dir: the directory to put the plotted figures (outputs)

entry_name_pattern: the (regular expression) patterns for fuzzers' entry names 

bucket: the time unit used to plot the "edge no over time".
(valid buckets are: "s", "m", "h", "sec", "min", "second", "minute", "hour", case does not matter)

max_span: maximum span for the fuzzing campaign (unit is hour)
```