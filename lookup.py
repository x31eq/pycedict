import cedict

target = cedict.decode_args()
if cedict.is_chinese(target):
    results = cedict.search_chinese(target)
else:
    english = list(cedict.search_english(target))
    pinyin = list(cedict.search_pinyin(target))
    results = english + pinyin
    if not results:
        # more liberal matching
        results = cedict.translations_with('', target)
cedict.print_lines(results)

