#! /bin/bash
export AFL_NO_AFFINITY=1

AFL_Binary=$1
Target=$2

Start_of_Tests=$3
Num_of_Tests=$4

Tmux_Session=$5
tmux has-session -t $Tmux_Session 2> /dev/null

if [[ $? != 0 ]]; then
    tmux new-session -d -s $Tmux_Session;
    for i in $(seq 1 $Num_of_Tests); do
        tmux new-window -t "$Tmux_Session:$i" -n "$Target-$i"  ;
        let output_dir_num="$i + $Start_of_Tests - 1";
        tmux send-keys  -t "$Tmux_Session:$i" "export AFL_NO_AFFINITY=1"   C-m ;
        tmux send-keys  -t "$Tmux_Session:$i" "$AFL_Binary -i in/ -o out-$output_dir_num/ -t 50 -d -p fast -- $Target @@"   C-m ;
    done;
fi;

