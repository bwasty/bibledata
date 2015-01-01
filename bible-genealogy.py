from __future__ import unicode_literals

from collections import namedtuple, OrderedDict
import os
import sys
from time import time

import pywikibot
import pandas as pd
import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_colwidth', 60)

LANG = 'en'
# LANG = 'de'


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

# Properties = {
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
# Properties['present_in_work'] = PropertyInfo('P1441', False)
Properties['instance_of'] = PropertyInfo('P31', False)
Properties['occupation'] = PropertyInfo('P106', False)
# Properties['brother'] = PropertyInfo('P7', True)
# Properties['sister'] = PropertyInfo('P9', True)
# }


# TODO: potentially interesting properties: occupation (Abraham: prophet - can be several...),
# instance of (moses: prophet),
# said to be the same as (Enoch: Metatron)
# part of (if no direct wiki entry -> Cain and Abel...)

PROPERTY_CACHE = {}


def import_data(df, person):
    """
    :type df: DataFrame
    :param person: ItemPage representing a person
    """

    referenced_persons = []

    row = pd.Series({
        'name': person.labels.get(LANG),
        LANG + 'wiki': person.sitelinks.get(LANG + 'wiki'),
        # 'description': person.descriptions.get(LANG)
    })

    for name, propinfo in Properties.iteritems():
        if propinfo.id not in person.claims:
            continue

        for value in person.claims[propinfo.id]:
            if name not in row:
                row[name] = []
            if propinfo.is_person:
                row[name].append(value.target.id)
                referenced_persons.append(value.target)
            else:
                target = value.target
                if not target:
                    continue
                if isinstance(target, pywikibot.WbTime):
                    row[name].append(target.year)
                else:
                    if target.id in PROPERTY_CACHE:
                        row[name].append(PROPERTY_CACHE[target.id])
                        progress(',')
                    else:
                        target.get()
                        progress()
                        value = target.labels.get(LANG)
                        row[name].append(value)
                        PROPERTY_CACHE[target.id] = value

        if len(row[name]) == 1:
            row[name] = row[name][0]

    row['url'] = "https://www.wikidata.org/wiki/" + person.id

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

    columns = ['name'] + Properties.keys() + ['description', LANG + 'wiki', 'url']
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
    MAX_RELATIVES = 250
    CSV_NAME = 'bible-genealogy.csv'
    ALWAYS_LIVE = False
    ALWAYS_LIVE = True
    ADAM = "Q70899"
    SHEM = "Q200902"
    ABRAHAM = "Q9181"
    DAVID = "Q41370"
    JESUS = "Q302"

    ROOT = ADAM

    if not ALWAYS_LIVE and os.path.exists(CSV_NAME):
        df = pd.DataFrame.from_csv(CSV_NAME)
    else:
        timer = Timer()
        df = loadFromWikidata(ROOT, MAX_RELATIVES)
        print
        timer.step('load from wikidata')
        df.to_csv('bible-genealogy.csv')

    print
    pretty_df = replace_name_references(df)
    print pretty_df
    # pretty_df_reduced = pretty_df[['name', 'gender', 'child', 'father']]
    # pretty_df_reduced['age'] = np.nan
    # pretty_df_reduced['fathers_age'] = np.nan
    # print pretty_df_reduced
    # pretty_df_reduced.to_csv('bible-genealogy-with-ages.csv')
    print "Numer of lines: ", len(df)


if __name__ == "__main__":
    main()