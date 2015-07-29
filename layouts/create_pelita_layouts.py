#!/usr/bin/env python3
# Use this script to update/regenerate the layouts strings in pelita.layouts.py

import os
import zlib
import base64
import pelita

EXTENSION = '.layout'
OUTFILENAME = '__layouts.py'

local_dir = os.path.dirname(os.path.realpath(__file__))
pelita_path = os.path.dirname(pelita.__file__)
outfile = os.path.join(pelita_path, OUTFILENAME)

content = '### This file is auto-generated. DO NOT EDIT! ###\n'
# loop through all layout files
for f in sorted(os.listdir(local_dir)):
    flname, ext = os.path.splitext(f)
    if ext != EXTENSION:
        continue
    with open(os.path.join(local_dir,f), 'rb') as bytemaze:
        layout = bytemaze.read()
        # create string variable
        content += 'layout_' + flname + ' = '
        # encode layout string
        content += '"""' + base64.encodebytes(zlib.compress(layout)).decode() + '"""\n'

# write out file in pelita directory
with open(outfile, 'w') as out:
    out.write(content)
