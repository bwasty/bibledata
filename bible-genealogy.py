from __future__ import unicode_literals

from collections import namedtuple, OrderedDict
import os
import sys
from time import time

import pywikibot
import pandas as pd
# import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 60)

LANG = 'en'
# LANG = 'de'

WIKIS = 'en', 'de'


class Timer:
    def __init__(self):
        self.started = time()

    def reset(self):
        now = time()
        diff = now - self.started
        self.started = now
        return diff

    def step(self, message):
        print '[%.3f s] %s' % (self.reset(), message)


def progress(indicator='.'):
    sys.stdout.write(indicator)
    sys.stdout.flush()

# property identifiers
PropertyInfo = namedtuple('PropertyInfo', 'id is_person')

Properties = OrderedDict()
Properties['spouse'] = PropertyInfo('P26', True)
Properties['child'] = PropertyInfo('P40', True)
Properties['gender'] = PropertyInfo('P21', False)
Properties['father'] = PropertyInfo('P22', True)
Properties['mother'] = PropertyInfo('P25', True)
Properties['born'] = PropertyInfo('P569', False)
Properties['died'] = PropertyInfo('P570', False)
Properties['birth_place'] = PropertyInfo('P19', False)
Properties['place_of_death'] = PropertyInfo('P20', False)
Properties['position_held'] = PropertyInfo('P39', False)
Properties['present_in_work'] = PropertyInfo('P1441', False)
Properties['instance_of'] = PropertyInfo('P31', False)

# Properties['occupation'] = PropertyInfo('P106', False)
# Properties['brother'] = PropertyInfo('P7', True)
# Properties['sister'] = PropertyInfo('P9', True)
# Properties['part of'] = PropertyInfo('P361', False)
# Properties['said to be the same as'] = PropertyInfo('P460', True)
# Properties['killed by'] = PropertyInfo('P157', True)
# Properties['given name'] = PropertyInfo('P735', False)
# Properties['noble family'] = PropertyInfo('P53', False)
# Properties['field of work'] = PropertyInfo('P101', False)
# Properties['member of'] = PropertyInfo('P463', False)
# Properties['religion'] = PropertyInfo('P140', False)
# Properties['location of burial'] = PropertyInfo('P119', False)
# Properties['cause of death'] = PropertyInfo('P509', False)
# Properties['manner of death'] = PropertyInfo('P1196', False)
# Properties['feast day'] = PropertyInfo('P841', False)
# Properties['residence'] = PropertyInfo('P551', False)
# Properties['country of citizenship'] = PropertyInfo('P27', False)
# Properties['ethnic group'] = PropertyInfo('P1074', False)
# Properties['native language'] = PropertyInfo('P103', False)
# Properties['canonization status'] = PropertyInfo('P411', False)

PROPERTY_CACHE = {}


# class Claim(object):
#     def __init__(self, id, label, source):
#         self.id = id
#         self.label = label
#         self.source = source
#
#     def __unicode__(self):
#         return self.label
#
#     def __str__(self):
#         return self.label


def get_property(claim_target):
    if claim_target.id in PROPERTY_CACHE:
        return PROPERTY_CACHE[claim_target.id]

    claim_target.get()
    progress(',')
    value = claim_target.labels.get(LANG)
    PROPERTY_CACHE[claim_target.id] = value
    return value


def abbreviate_book(book):
    return book[:3]


def parse_bible_source(source):
    try:
        book = source['P248'][0].target
        book_name = get_property(book)  # book.labels.get(LANG)
        chapter = source['P792'][0].target
        verse = source['P958'][0].target
    except KeyError:
        return None
    return "{} {}:{}".format(abbreviate_book(book_name), chapter, verse)


def parse_claim(claim):
    claim.get()
    parsed = {'id': claim.id,
              'label': claim.labels.get(LANG),
              'sources': [source.id for source in claim.sources]}


def import_data(df, person):
    """
    :type df: DataFrame
    :param person: ItemPage representing a person
    """

    referenced_persons = []

    row = pd.Series({
        'name': person.labels.get(LANG),
        'description': person.descriptions.get(LANG)
    })

    if LANG in person.aliases:
        row['aliases'] = person.aliases[LANG]

    for wikilang in WIKIS:
        row[wikilang + 'wiki'] = person.sitelinks.get(wikilang + 'wiki')

    for name, propinfo in Properties.iteritems():
        if propinfo.id not in person.claims:
            continue

        for claim in person.claims[propinfo.id]:
            if name not in row:
                row[name] = []
            if propinfo.is_person:
                entry = [claim.target.id]
                # row[name].append(claim.target.id)
                referenced_persons.append(claim.target)
                for source in claim.sources:
                    entry.append(parse_bible_source(source))

                row[name].append(entry)
            else:
                # TODO!!: create pairs (id, label/value, reference?) instead
                target = claim.target
                if not target:
                    continue
                if isinstance(target, pywikibot.WbTime):
                    row[name].append(target.year)
                else:
                    row[name].append(get_property(target))
                    # if target.id in PROPERTY_CACHE:
                    #     row[name].append(PROPERTY_CACHE[target.id])
                    #     progress(',')
                    # else:
                    #     target.get()
                    #     progress()
                    #     value = target.labels.get(LANG)
                    #     # claim = Claim(target.id, target.labels.get(LANG), value.sources)
                    #     row[name].append(value)
                    #     PROPERTY_CACHE[target.id] = value

        if len(row[name]) == 1:
            row[name] = row[name][0]

    df.loc[person.id] = row

    return referenced_persons


def replace_name_references(df):
    """
    :type df: pd.DataFrame
    """
    is_reference = lambda x: isinstance(x, unicode) and x.startswith('Q') and x[1].isdigit()

    def mapper(x):
        if is_reference(x) and x in df.index:
            return df.loc[x]['name']
        elif isinstance(x, list):
            newlist = []
            for y in x:
                if y in df.index:
                    newlist.append(df.loc[y]['name'])
                else:
                    newlist.append(unicode(y))

            return ', '.join(newlist)

        return x
    return df.applymap(mapper)


def loadFromWikidata(root_id, max_relatives):
    wikidata = pywikibot.Site("wikidata", "wikidata")
    repo = wikidata.data_repository()

    root_person = pywikibot.ItemPage(repo, root_id)
    root_person.get()
    progress('|')

    columns = ['name', 'aliases'] + Properties.keys() + ['description'] + [wikilang + 'wiki' for wikilang in WIKIS]
    df = pd.DataFrame(columns=columns)
    df.index.name = "id"

    referenced_persons = import_data(df, root_person)
    while len(df) < max_relatives and referenced_persons:
        person = referenced_persons.pop(0)
        if person.id not in df.index:
            person.get()
            progress('|')

            referenced_persons.extend(import_data(df, person))

    return df


def main():
    MAX_RELATIVES = 50
    CSV_NAME = 'bible-genealogy.csv'
    ALWAYS_LIVE = False
    ALWAYS_LIVE = True
    ADAM = "Q70899"
    SHEM = "Q200902"
    ABRAHAM = "Q9181"
    DAVID = "Q41370"
    JESUS = "Q302"

    # TODO!: how get non-connected people like John the baptist, Apostles? Query by claim possible here?
    # Likely only choice: https://wdq.wmflabs.org/wdq/

    ROOT = ADAM

    if not ALWAYS_LIVE and os.path.exists(CSV_NAME):
        df = pd.DataFrame.from_csv(CSV_NAME)
    else:
        timer = Timer()
        df = loadFromWikidata(ROOT, MAX_RELATIVES)
        print
        timer.step('load from wikidata')
        df.to_csv('bible-genealogy.csv', encoding='utf-8')

    # print
    # pretty_df = replace_name_references(df)
    # print pretty_df
    # pretty_df_reduced = pretty_df[['name', 'gender', 'child', 'father']]
    # pretty_df_reduced['age'] = np.nan
    # pretty_df_reduced['fathers_age'] = np.nan
    # print pretty_df_reduced
    # pretty_df_reduced.to_csv('bible-genealogy-with-ages.csv')
    print "Numer of lines: ", len(df)


if __name__ == "__main__":
    main()
