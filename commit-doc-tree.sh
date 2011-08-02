#!/bin/zsh

# check, if index is empty
if git diff-index --cached --quiet --ignore-submodules HEAD ; then
  echo "Cannot work with indexed files. Aborting."
fi

# get the SHA1 of the current commit
head_sha=$( git rev-parse HEAD)
head_sha=$head_sha[0,7]

# make the documentation
echo "Generating doc from $head_sha"
cd doc
make clean ; make
cd ..

docdirectory=doc/build/html/

# Adding the doc files to the index
git add -f $docdirectory

# writing a tree
tree=$(git write-tree --prefix=doc/build/html/)

# we’ll have a commit
commit=$(echo "DOC: Sphinx generated doc from $head_sha" | git commit-tree $tree -p gh-pages)

# one up
git update-ref refs/heads/gh-pages $commit

# clean index
git reset HEAD

