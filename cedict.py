from __future__ import generators
"""Common stuff for working with CEDICT"""

import sys, os, re, unicodedata
try:
    from sqlite3 import dbapi2
except ImportError:
    from pysqlite2 import dbapi2

folder = sys.path[0]

common_words = "a an and for in n of one or s the to .".split()

# Catch anything that might be chinese characters.
# Crude, but works with UTF-8, GB-2312,
# and proper unicode strings.
# Assumes everything else is ASCII.
chinese_expr = r'[^\x00-\x7f](?:\.|[^\x00-\x7f])*'

line_expr = '^(?:(\S+)\s+)?(\S+)\s+\[([^]]+)\]\s+/(.*)/\s*$'

# Catch English words.
# Designed so it doesn't catch Chinese words.
# Recognizes the e with a circumflex used in some place names
# but not foreign words in general.
# No pin yin for now.
word_expr = u'[\\w\xca\xea]+'

chunk_expr = chinese_expr + '|' + chinese_expr.replace('^', '')

input_encoding = sys.stdin.encoding or 'utf-8'
# use input encoding for output for pipes
output_encoding = sys.stdout.encoding or input_encoding
dbname = os.path.join(folder, 'cedict.db')

def search_chinese(target):
    for entry in search_first_character(target):
        traditional = entry[0]
        simplified = entry[1]
        if simplified.startswith(target) or (
                traditional and traditional.startswith(target)):
            yield entry

def search_english(target):
    target_string = clean_punctuation(target)
    for entry in translations_with('', target):
        raw_translation = entry[3]
        translation = clean_punctuation(raw_translation)
        translated_words = get_words('', raw_translation)
        if re.search(r'(?i)\b'+target_string+r'\b',translation):
            yield entry

def search_pinyin(target):
    pinyinTargets = re.findall(r'\b[a-z:]+\d?', target.lower().replace("v","u:"))
    if not pinyinTargets:
        return
    for entry in translations_with(' '.join(pinyinTargets), ''):
        pinyin = entry[2]
        if pinyinTargets and len(pinyin) >= len(pinyinTargets):
            for syl, tar in zip(pinyin.split(), pinyinTargets):
                if re.search('\d', tar):
                    if syl != tar:
                        break
                elif re.findall('\D+', syl)[0] != tar:
                        break
            else:
                yield entry

def translations_with(pinyin, english):
    words = get_words(pinyin, english)
    query = "intersect".join(["""
        select traditional, simplified, pinyin, english
        from translations
        join word_in_translation
        on translations.translation_id = word_in_translation.translation_id
        and word=?
        """]*len(words))
    return db.cursor().execute(query, words)

def search_first_character(target):
    first_character = target[:1]
    result = db.cursor().execute("""
                select traditional, simplified, pinyin, english
                from translations
                where first_traditional=?
                or first_simplified=?
                """,
                (first_character, first_character)).fetchall()
    if not result:
        raise ValueError("character not found: %r" % first_character)
    return result

def translate_line(line):
    for chunk in get_chunks(line):
        if is_chinese(chunk):
            next_word(chunk)
        else:
            print(chunk.encode(output_encoding))

def next_word(target):
    """look recursively for the next longest match"""
    if not target:
        return
    try:
        longest = 0 # find the longest match
        result = []
        for entry in search_first_character(target):
            for characters in entry[0], entry[1]:
                if characters and len(characters)>=longest and target.find(characters)==0:
                    if longest==len(characters):
                        result.append(entry)
                    else:
                        result = [entry]
                        longest = len(characters)
        print_lines(result)
        next_word(target[max(longest,1):])
    except ValueError:
        fail(target[:1])
        next_word(target[1:])


def fail(chinese_text):
    """report that no match was found"""
    for character in chinese_text:
        try:
            character_name = unicodedata.name(character)
        except ValueError:
            print_error(repr(character), "not found")
        else:
            encoded_character = character.encode(output_encoding)
            if isinstance(encoded_character, str):
                # python2
                character = encoded_character
            print('%s %s' % (character, character_name))

def decode_args():
    joined = ' '.join(sys.argv[1:])
    if hasattr(joined, 'decode'):
        return joined.decode(input_encoding)
    return joined

def is_chinese(text):
    return text and text[0] > '\x7f'

def decodeline(line):
    parsed = re.findall(line_expr, line)
    if not parsed:
        print_error("Format not recognized")
        print_error(repr(line))
    trad, simp, pinyin, translation = parsed[0]
    return trad, simp, pinyin.lower(), translation

def print_lines(entries):
    for entry in entries:
        traditional, simplified, pinyin, translation = entry
        result = "%s [%s] %s" % (simplified, pinyin, translation)
        if traditional and traditional != simplified:
            result =  "%s (%s)" % (result, traditional)
        try:
            encoded = result.encode(output_encoding)
            if isinstance(encoded, str):
                # python2
                print(encoded)
            else:
                print(result)
        except ValueError as err:
            print_error('failed on', repr(entry), repr(err))

def clean_punctuation(english):
    return " ".join(re.findall(word_expr, english.lower()))

def get_words(pinyin, english):
    """Return English words or Pin Yin syllables that the database indexes."""
    # It's important that the same function is used
    # for both reading and writing the database!
    result = []
    for word in re.findall(word_expr, english.lower()):
        if word in common_words:
            continue
        # Truncating to 6 letters keeps the database small.
        word = word[:6]
        if word not in result:
            result.append(word)
    for word in pinyin.split():
        word = word.replace('u:', 'v')
        # don't worry about the tones
        if word[-1].isdigit():
            word = word[:-1]
        if word not in result:
            result.append(word)
    return result

def get_chunks(text):
    """return complete runs of either Chinese or not"""
    return re.findall(chunk_expr, text.strip())

def print_error(*words):
    sys.stderr.write(' '.join(words))
    sys.stderr.write('\n')

db = dbapi2.connect(dbname)
