import cedict, os

def makedb(dbname, filename, encoding='utf8'):
    if os.path.exists(dbname):
        os.remove(dbname)
    db = cedict.dbapi2.connect(dbname)
    cur = db.cursor()
    cur.execute("""
        create table translations (
            translation_id integer primary key not null,
            first_traditional,
            traditional,
            first_simplified not null,
            simplified not null,
            pinyin not null,
            english not null
        )""")
    db.commit()
    cur.execute("""
        create table word_in_translation(
            word not null,
            translation_id not null references translations(translation_id),
            primary key (word, translation_id)
        )
        """)

    for line in file(filename):
        if line.strip()=='' or line[0]=='#':
            continue
        line = line.decode(encoding)
        trad, simp, pinyin, english = cedict.decodeline(line)
        first_simp = simp[:1]
        if trad==simp:
            trad = first_trad = None
        else:
            first_trad = trad[:1]
        cur.execute("""
                insert into translations(
                    first_traditional, traditional,
                    first_simplified, simplified,
                    pinyin, english)
                values(?, ?, ?, ?, ?, ?)
                """,
                (first_trad, trad, first_simp, simp, pinyin, english))
        id = cur.lastrowid
        for word in cedict.get_words(pinyin, english):
            cur.execute("""
                insert into word_in_translation
                    (word, translation_id)
                    values(?, ?)
                """, (word, id))

    # create the indexes last for efficiency
    cur.execute("create index simp_index on translations (first_simplified)")
    if encoding:
        cur.execute("create index trad_index on translations (first_traditional)")
    cur.execute("create index word_index on word_in_translation (word)")
    db.commit()

makedb("cedict.db", "cedict_1_0_ts_utf-8_mdbg.txt", "utf8")
