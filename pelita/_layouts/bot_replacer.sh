#!bin/bash

for filename in *.layout; do
	sed -i.bu 's/0/a/g' $filename;
	sed -i.bu 's/1/x/g' $filename;
	sed -i.bu 's/2/b/g' $filename;
	sed -i.bu 's/3/y/g' $filename;
done
