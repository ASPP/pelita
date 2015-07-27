#!/bin/sh

# Script to automatically generate documentation and write this
# to a git tree. See http://ASPP.github.com/pelita/development.rst
# for more information.

# check, if index is empty
if ! git diff-index --cached --quiet --ignore-submodules HEAD ; then
  echo "Fatal: cannot work with indexed files!"
  exit 1
fi

# get the 'git describe' output
git_describe=$(git describe)


# Generate _contributors.rst
CONTRIBUTORS=doc/source/_contributors.rst

echo "As of \`\`${git_describe}\`\` the developers and contributors are::" > $CONTRIBUTORS
echo "" >> $CONTRIBUTORS
git shortlog -sn | awk '{first = $1; $1 = "   "; print $0; }' >> $CONTRIBUTORS

# make the documentation, hope it doesn't fail
echo "Generating doc from $git_describe"
(cd doc; git clean -n -x -d)
(cd doc; make clean)
if ! (cd doc; make html) ; then
  echo "Fatal: 'make'ing the docs failed cannot commit!"
  exit 2
fi

docdirectory=doc/build/html/

# Add a .nojekyll file
# This prevents the GitHub jekyll website generator from running
touch $docdirectory".nojekyll"

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
