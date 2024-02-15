# namor_data
The raw data behind the [namor](https://github.com/DLu/namor/) Python library, and tools for updating it.

### Initial Data Source
Building on the work of [jonathanhar](https://github.com/jonathanhar/diminutives.db),
the initial data source for this project is the categories on [Wiktionary](https://en.wiktionary.org),
starting with all of the names that fall into the [categories of given names by language](https://en.wiktionary.org/wiki/Category:Given_names_by_language).
The template [`given_name`](https://en.wiktionary.org/wiki/Template:given_name) is then used to get properties of those names, including diminutive forms of the names.

### Library Comparisons
There are several other data sources that provide data on names / nicknames.

| Name / Link | Description | # of entries |
|-------------|-------------|--------------|
| [common_nickname_csv](https://github.com/onyxrev/common_nickname_csv/blob/master/nicknames.csv) | Git controlled CSV with nicknames | 1432
| [nicknames](https://github.com/carltonnorthern/nicknames) | Multiple programming language library (available via pip) based on geneaology data | 1080 |
| [Lingua-En-Nickname](https://github.com/brianary/Lingua-EN-Nickname/blob/main/nicknames.txt) | Perl library with multiple data sources | 563 |
| [diminutives.db](https://github.com/jonathanhar/diminutives.db/blob/master/male_diminutives.csv) | Git controlled CSV based on wiktionary | 545 |
| [Common Nicknames by Deron Meranda](https://web.archive.org/web/20181022154748/https://deron.meranda.us/data/nicknames.txt) | (defunct, via web.archive.org) List of nicknames from census data. Also includes likelihood scores | 523
| [SOEMPI](https://github.com/MrCsabaToth/SOEMPI/blob/master/openempi/conf/name_to_nick.csv) | Nicknames CSV as part of a larger patient data project | 464 |

The data contained in this repo references over 7,000 English names and over 40,000 names total.
