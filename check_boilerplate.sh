#!/bin/zsh



check_docformat(){
    if ! grep -q '__docformat__' $1 ; then
        echo "warning: file '$1' does not conatin a '__docformat__' declaration!"
    fi
}

check_coding(){
    if ! grep -q -e 'coding: utf-8' $1 ; then
        echo "warning: file '$1' does not conatin a coding declaration!"
    fi
}


for f in $( ls pelita/**/*.py ) ; do
    check_docformat $f
    check_coding $f
done
