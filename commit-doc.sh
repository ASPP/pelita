#!/bin/zsh

# get the SHA1 of the current commit
head_sha=$( git rev-parse HEAD)
head_sha=$head_sha[0,7]

# make the documentation
echo "Generating doc from $head_sha"
cd doc
make clean ; make
cd ..

# checkout the doc-branch
git checkout gh-pages
# create a temp dir, and copy doc files there
tmp_dir=$( mktemp -dt pelita.gh-pages.XXXXXXXXXX)
echo $tmp_dir
cp -r doc/build/html/* $tmp_dir

# clean the root dir and copy doc files back
git clean -dfx
cp -r $tmp_dir/* .

# assuming eevrything went well, add all files in root dir
# and create a commit
git add .
git commit -m "Sphinx generated doc from: $head_sha"

