#!/bin/bash

# Usage: ./memcheck.sh <pid> <secret_data1> [<secret_data2> ...]

pid="$1"
shift

sudo gcore $pid
for secret_data in $@; do
    printf "\n"
    if grep "$secret_data" core.$pid ; then
        printf "TEST FAILED: $secret_data was found\n"
    else
        printf "TEST PASSED: $secret_data was NOT found\n"
    fi
done
rm -rf core.$pid &



