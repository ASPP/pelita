#!/bin/zsh

# Small script to do a QA of the code. Will print total lines of code, the
# summary score of pylint and the results of testing. This is designed to give a
# one page, easy-to-read summary of a few code quality metrics.

do_wc(){
    # LOC does not count blanklines
    LOC=$( find $@ -name '*.py' -print0 | xargs --null sed "/^\s*$/d" |
           wc -l | tail -1 | sed 's/total//' )
    # LOC-COM counts comments. Comments are lines whose first non-blank character
    # is a single '#'. Lines where the first two non-blank characters are 
    # '##' are not counted as comments [we use that for maze layouts].
    COM=$( find $@ -name '*.py' -print0 | xargs --null sed "/^\s*$/d" |
           # put a placeholder in front of lines with '##'
           sed  "s/^\s*##.*$/PLACEHOLDER/" |
           # now remove comments
           sed "/^\s*#.*$/d" | wc -l | tail -1 | sed 's/total//' )
    PERCENT=$(echo "scale=1;$(( $LOC - $COM ))*100/$LOC"|bc) 
    print $LOC of which $(( $LOC - $COM )) \($PERCENT\%\) are comments
}

do_pylint(){
    print $( pylint $@ &> /dev/null |
        grep 'Your code' |
        sed 's/Your\ code\ has\ been\ rated at\ \([^ ]*\) .*$/\1/' )
}

echo "Project summary / QA for pelita"
echo "----------------------------------------------------------------------"
echo "Lines of code:"
for d in pelita test pelita/messaging; do
printf "%30s : %20s\n" $d "$( do_wc $d )"
done
echo ""

if ! which pylint &> /dev/null ; then
    echo "pylint not found in path! Can't do style checker!"
else
    echo "Running pylint... please stand by!"
    echo "Pylint score:"
    echo "  for pelita/               : "$(do_pylint pelita/**/*.py )
    echo "  for test/                 : "$( do_pylint test/**/*.py )
    echo "  for both/                 : "$( do_pylint {pelita,test}/**/*.py )
fi

if ! which nosetests &> /dev/null ; then
    echo "'nosetests' not found in path! Can't run tests!"
else
    echo ""
    echo "Running tests... please stand by!"
    test_stats=$( nosetests --with-cov --cover-package pelita 2>&1 >/dev/null)
    echo "  Total number of tests     : "$( echo $test_stats |
        grep 'Ran'|
        sed 's/Ran\ \(.*\)\ tests.*/\1/' )
    echo "  # assert statements       : "$( grep 'assert' test/**/*.py | wc -l)
    echo "  Test coverage             : "$( echo $test_stats |
        grep 'TOTAL' |  sed 's/TOTAL.*\(......$\)/\1/')
    echo "  Result                    : "$( echo $test_stats | tail -1)
fi

