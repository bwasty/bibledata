Bibledata
=========

The python scripts require [pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot) to be installed, configured and available in `PYTHONPATH`

* `bible-genealogy.csv` contains a dump of all biblical characters that can be reached via `child/spouse/father/mother` relations (the properties that are converted to columns are hardcoded in `bible-genealogy.py`)
* `bible-genealogy-with-ages.csv` is a work-in-progress with additional information and references manually extracted from the bible. Should end up in Wikidata eventually (for `age` and `fathers_age` there are no fitting properties yet afaik).
