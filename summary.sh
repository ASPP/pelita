#!/bin/zsh

# Small script to do a QA of the code. Will print total lines of code, the
# summary score of pylint and the results of testing. This is designed to give a
# one page, easy-to-read summary of a few code quality metrics.

do_wc(){
    print $(wc -l $@ | tail -1 | sed 's/total//')
}

do_pylint(){
    print $( pylint $@ &> /dev/null |
        grep 'Your code' |
        sed 's/Your\ code\ has\ been\ rated at\ \([^ ]*\) .*$/\1/' )
}

echo "Project summary / QA for pelita"
echo "----------------------------------------------------------------------"
echo "Lines of code:"
echo "  in pelita/                : "$( do_wc pelita/**/*.py )
echo "  in test/                  : "$( do_wc test/**/*.py )
echo "  in pelita/messaging       : "$( do_wc pelita/messaging/**/*.py )
echo "  in all                    : "$( do_wc {pelita,test}/**/*.py )
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
    test_stats=$( nosetests --with-coverage --cover-package pelita 2>&1 >/dev/null)
    echo "  Total number of tests     : "$( echo $test_stats | grep 'Ran' | sed 's/Ran\ \(.*\)\ tests.*/\1/' )
    echo "  # assert statements       : "$( grep 'assert' -c test/**/*.py | sed 's/.*://' | \
        python -c "import sys; print sum(int(l) for l in sys.stdin)" )
    echo "  Test coverage             : "$( echo $test_stats | grep 'TOTAL' |  sed 's/TOTAL.*\(......$\)/\1/')
    echo "  Result                    : "$( echo $test_stats | tail -1)
fi

