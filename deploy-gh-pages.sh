#!/bin/bash

BRANCH="master"

if
  [ "$TRAVIS_REPO_SLUG" == "$REPO" ] &&
  [ "$TRAVIS_PULL_REQUEST" == "false" ] &&
  [ "$TRAVIS_PYTHON_VERSION" == "3.6" ] &&
  [ "$PYZMQ" == "pyzmq" ] &&
  [ "$TRAVIS_BRANCH" == "$BRANCH" ]; then

  echo "Trying to build documentation."

  pip install Sphinx

  cd $HOME
  git config --global user.email "travis@travis-ci.org"
  git config --global user.name "travis-ci"
  git clone --quiet --branch=$BRANCH https://${GH_TOKEN}@github.com/${REPO} pelitadoc

  cd pelitadoc

  git checkout gh-pages
  git checkout $BRANCH

  TREEFILE=$(mktemp TREE.XXXXXX)

  ./make-doc-tree.sh $TREEFILE

  tree=$(cat $TREEFILE)

  # get the ‘git describe’ output
  git_describe=$(git describe)

  # we’ll have a commit
  commit=$(echo "DOC: Sphinx generated doc from $git_describe" | git commit-tree $tree -p gh-pages)

  # move the branch to the commit we made, i.e. one up
  git update-ref refs/heads/gh-pages $commit

  git push -q origin gh-pages

fi
