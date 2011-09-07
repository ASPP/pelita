#!/bin/zsh

# Script to automatically generate documentation and commit this to the gh-pages
# branch. See README.md for more info about website maintenance and updates.

# check, if index is empty
if ! git diff-index --cached --quiet --ignore-submodules HEAD ; then
  echo "Cannot work with indexed files. Aborting."
  exit
fi

# get the 'git describe' output
git_describe=$( git describe)

# make the documentation
echo "Generating doc from $git_describe"
cd doc
make clean ; make
cd ..

docdirectory=doc/build/html/

# Add a .nojekyll file for sphinx
touch $docdirectory".nojekyll"

# Adding the doc files to the index
git add -f $docdirectory

# writing a tree
tree=$(git write-tree --prefix=doc/build/html/)

# we’ll have a commit
commit=$(echo "DOC: Sphinx generated doc from $git_describe" | git commit-tree $tree -p gh-pages)

# one up
git update-ref refs/heads/gh-pages $commit

# clean index
git reset HEAD

# try to checkout what we’ve done – does not matter much, if it fails
# it is purely informative
git checkout gh-pages

