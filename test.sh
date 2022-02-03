#!/bin/bash
#C:\\Users\\haji.uduman\\Downloads\\codeql\\codeql resolve languages  | head -n1  | cut -d " " -f1
#my_array = ( $(C:\\Users\\haji.uduman\\Downloads\\codeql\\codeql resolve languages) )
#IFS=$'\n'
readarray -t my_array < <(C:\\Users\\haji.uduman\\Downloads\\codeql\\codeql resolve languages)
#IFS=$'\r\n' read -r -d '' -a my_array < <( C:\\Users\\haji.uduman\\Downloads\\codeql\\codeql resolve languages )
#declare -p my_array

for i in "${!my_array[@]}"; do
    stringarray=(${my_array[i]})
    printf '%s\n' "${stringarray[0]}"
done

# for (( i=0; i<${my_array}; i++ ));
# do
#   echo "index: $i"
# done