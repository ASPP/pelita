#!/bin/zsh

# Script to automatically generate documentation and commit this to the gh-pages
# branch. See README.md for more info about website maintenance and updates.

# get the SHA1 of the current commit
head_sha=$( git rev-parse HEAD)
head_sha=$head_sha[0,7]

# make the documentation
echo "Generating doc from $head_sha"
cd doc
make clean ; make
cd ..

# checkout the doc-branch
git checkout gh-pages || exit 1

# create a temp dir, and copy doc files there
tmp_dir=$( mktemp -dt pelita.gh-pages.XXXXXXXXXX)
echo $tmp_dir
cp -r doc/build/html/* $tmp_dir
rm -rf doc

# clean the root dir and copy doc files back
# but abort if there are untracked files present
if git status --porcelain | grep '??' &> /dev/null ; then
    echo "There are unttarcked files present, aborting!"
    git status
    git checkout -
    exit 1
fi
git clean -dfx
cp -r $tmp_dir/* .

# assuming eevrything went well, add all files in root dir
# and create a commit
git add .
git commit -m "DOC: Sphinx generated doc from: $head_sha"
echo "Ready to push documentation to github!"

