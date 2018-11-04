#!/bin/sh

# Script to automatically generate documentation and write this
# to a git tree. See http://ASPP.github.com/pelita/development.rst
# for more information.

# check, if index is empty
if ! git diff-index --cached --quiet --ignore-submodules HEAD ; then
  echo "Fatal: cannot work with indexed files!"
  exit 1
fi

./build-docs.sh

docdirectory=doc/build/html/

# Adding the doc files to the index
git add -f $docdirectory

# writing a tree using the current index
tree=$(git write-tree --prefix=$docdirectory)

# reset the index
git reset HEAD

if [ "$#" -eq 1 ]; then
  echo "New tree $tree. Writing to file $FILE"
  echo $tree > $1
else
  echo "New tree $tree."
fi
