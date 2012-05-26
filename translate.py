"""Translate a Chinese text verbatim to PinYin and English"""

import sys, cedict

input_string = cedict.decode_args()

if cedict.is_chinese(input_string):
    cedict.translate_line(input_string)
else:
    # take the input as a filename
    if input_string=='-':
        input_file = sys.stdin
    else:
        input_file = file(input_string)
    for line in input_file:
        cedict.translate_line(line.decode('utf-8')) # no other encodings for now
