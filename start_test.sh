#! /bin/bash

usage ()
{
    echo 'Usage: ./start_test.sh <afl-binary> <target-binary> <start of n in out-n/> <number of tests> <session name of tmux>'
    echo 'Example: ./start_test.sh `which afl-fuzz` ./pngfix 6 6 pngfix-afl-2.52b'
    exit 1
}

if [[ ! -z $1 ]]
then
    [[ `command -v $1` ]] || { echo "$1 command not found! Aborting."; usage;}
fi

if [[ ! -z $2 ]]
then
    [[ -f $2 ]] || { echo "Target binary not found! Aborting.";usage;}
fi

if [[ ! -z $3 ]]
then
    if [[ -d "out-$3" ]]
    then
        echo "./out-$3/ exists, danger! Aborting.";
        usage;
    fi
    if [[ ! $3 =~ ^[0-9]+$ ]]
    then
        echo "$3 is not a positive number. Aborting."
        usage;
    fi
fi

if [[ ! -z $4 ]] && [[ ! $4 =~ ^[0-9]+$ ]] 
then
    echo "$4 is not a positive number. Aborting"
    usage;
fi


if [[ "$#" -ne 5 ]]
then usage
fi


AFL_Binary=$1
Target=$2
Start_of_Tests=$3
Num_of_Tests=$4
Tmux_Session=$5

tmux has-session -t $Tmux_Session 2> /dev/null;

if [[ $? != 0 ]]; then
    tmux new-session -d -s $Tmux_Session;
    for i in $(seq 1 $Num_of_Tests); do
        tmux new-window -t "$Tmux_Session:$i" -n "$Target-$i"  ;
        let output_dir_num="$i + $Start_of_Tests - 1";
        tmux send-keys  -t "$Tmux_Session:$i" "export AFL_NO_AFFINITY=1"   C-m ;
        tmux send-keys  -t "$Tmux_Session:$i" "$AFL_Binary -i in/ -o out-$output_dir_num/ -t 50 -d -p fast -- $Target @@"   C-m ;
    done;
else
    printf "tmux session $Tmux_Session exists.\n=========\n`tmux ls 2>/dev/null`."
fi;

