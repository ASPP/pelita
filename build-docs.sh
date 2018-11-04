#!/bin/sh

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

