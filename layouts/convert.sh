#!/bin/sh
grep -q 0 $1 && echo "Fatal: Layout $1 was already converted." && exit 1
sed -e 's:\%:\#:g' -e 's:1:0:' -e 's:2:1:' -e 's:3:2:' -e 's:4:3:' $1 > tmp
mv tmp $1
