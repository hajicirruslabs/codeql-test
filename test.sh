#!/bin/bash
codeql_path=C:\\Users\\haji.uduman\\Downloads\\codeql
readarray -t codeql_languages < <($codeql_path\\codeql resolve languages)
languages=()

for i in "${!codeql_languages[@]}"; do
    stringarray=(${codeql_languages[i]})
    languages+=(${stringarray[0]})
done

db_path=/c/Users/haji.uduman/Desktop/db
readarray -t db_folders < <(ls -d $db_path/*/)

echo ===================================
repo_languages=()
for i in "${!db_folders[@]}"; do
    stringarray=($(basename ${db_folders[i]}))
    case "${languages[@]}" in  *"${stringarray[0]}"*) repo_languages+=(${stringarray[0]}) ;; esac
done

echo ===================================

for i in "${!languages[@]}"; do
    printf '%s\n' "${languages[i]}"
done

echo ===================================

for i in "${!repo_languages[@]}"; do
    printf '%s\n' "${repo_languages[i]}"
done


if [ ${#repo_languages[@]} -eq 1 ]; then
    echo "One"
elif [ ${#repo_languages[@]} -gt 1 ]; then
    echo "More than one"
fi

if [ -e x.txt ]
then
    echo "ok"
else
    echo "nok"
fi
