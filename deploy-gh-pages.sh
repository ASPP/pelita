#!/bin/sh

if
  [ "$TRAVIS_REPO_SLUG" == "ASPP/pelita" ] &&
  [ "$TRAVIS_PULL_REQUEST" == "false" ] &&
  [ "$TRAVIS_PYTHON_VERSION" == "3.4" ] &&
  [ "$PYZMQ" == "pyzmq" ] &&
  [ "$TRAVIS_BRANCH" == "master" ]; then

  echo "Trying to build documentation."

  cd $HOME
  git config --global user.email "travis@travis-ci.org"
  git config --global user.name "travis-ci"
  git clone --quiet --branch=master https://${GH_TOKEN}@github.com/ASPP/pelita pelitadoc

  pip install Sphinx
  pip install numpydoc

  cd pelitadoc

  TREEFILE=$(mktemp TREE.XXXXXX)

  ./make-doc-tree.sh $TREEFILE

  TREE=$(cat $TREEFILE)

  # get the ‘git describe’ output
  git_describe=$(git describe)

  # we’ll have a commit
  commit=$(echo "DOC: Sphinx generated doc from $git_describe" | git commit-tree $tree -p gh-pages)

  # move the branch to the commit we made, i.e. one up
  git update-ref refs/heads/gh-pages $commit

  git push -fq origin gh-pages

fi
