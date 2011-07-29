#!/bin/zsh



check_docformat(){
    if ! grep -q '__docformat__' $1 ; then
        echo "warning: file '$1' does not conatin a '__docformat__' declaration!"
    fi
}

for f in $( ls pelita/**/*.py ) ; do
    check_docformat $f
done
