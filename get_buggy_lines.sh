#!/usr/bin/env bash

# Diff between the faulty and fixed versions. It reports line numbers for removed
# and added lines in the faulty version.
# file="org/apache/commons/cli/Parser.java"; \
file=$1
fault_path=$2
fixed_path=$3
project_name=$4
diff \
    --unchanged-line-format='' \
    --old-line-format="$file#%dn#%l%c'\12'" \
    --new-group-format="$file#%df#FAULT_OF_OMISSION%c'\12'" \
    $2 $3 > /tmp/all_faulty_lines.txt; \
# Print all removed lines to /tmp/buggy.lines
grep --text --invert-match "FAULT_OF_OMISSION" /tmp/all_faulty_lines.txt > /tmp/$project_name.buggy.lines; \
# Check which added lines need to be added to /tmp/buggy.lines. Determine whether
# file#line already exists in /tmp/buggy.lines. If so, skip it.
for entry in $(grep --text 'FAULT_OF_OMISSION' /tmp/all_faulty_lines.txt); do \
    line=$(echo $entry | cut -f1,2 -d'#'); \
    grep --text --quiet "$line" /tmp/$project_name.buggy.lines || echo "$entry" >> /tmp/$project_name.buggy.lines; \
done

rm /tmp/all_faulty_lines.txt