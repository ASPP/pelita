#!/bin/zsh

check_coding(){
    if ! grep -q -e 'coding: utf-8' $1 ; then
        echo "warning: file '$1' does not contain a coding declaration!"
    fi
}

for f in $( ls pelita/**/*.py ) ; do
    check_coding $f
done
