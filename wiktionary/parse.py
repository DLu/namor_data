import argparse
import collections
import click
import datetime
import langcodes
import mwparserfromhell
from tqdm import tqdm
import re

from . import WiktionaryDB, Relationship, GenderFlag
from .scrape import CAT_PREFIX


LANGUAGE_PREFIX = re.compile(CAT_PREFIX + r'\w\w:.*$')
LANG_GIVEN_NAMES = re.compile(CAT_PREFIX + r'(.*?) (male |female |unisex |)given names( from (.+))?$')
TRAILING_NUMBER = re.compile(r'([a-z_]+)(\d+)')
TEMPLATE_ARGS = {
    'given name': {
        1: 'lang',
        2: 'gender',
        3: 'from',
        4: 'from',
        5: 'from',
    },
    'alternative form of': {
        1: 'lang',
        2: 'alt',
    },
    'historical given name': {
        1: 'lang',
        2: 'gender',
        3: 'notorious'
    }
}


languages = collections.Counter()
stats = collections.Counter()


def merge_dict(a, b):
    for name, value in b.items():
        if name not in a:
            a[name] = value
        elif isinstance(value, set):
            if isinstance(a[name], list):
                a[name] = set(a[name])
            if isinstance(a[name], set):
                for v in value:
                    a[name].add(v)
            else:
                raise RuntimeError(f'Cannot merge {type(a[name])} with set')
        else:
            raise NotImplementedError(f'No implementation for merging {type(value)}')


def parse_category(cat_name, debug=False):
    info = {}
    m = LANGUAGE_PREFIX.match(cat_name)
    if m:
        if debug:
            click.secho(f'Skipping page with language prefix: {cat_name}', fg='yellow')
        return info
    warning = False
    m = LANG_GIVEN_NAMES.match(cat_name)
    if m:
        language_s, gender_s, _, origin_s = m.groups()
        try:
            info['cat.lang'] = str(langcodes.find(language_s))
        except LookupError:
            languages[language_s] += 1
            if debug:
                click.secho(f'Skipping unknown language {language_s}', fg='yellow')
            warning = True

        gender_s = gender_s.strip()
        if gender_s:
            info['cat.gender'] = gender_s

        if origin_s:
            try:
                info['cat.origin'] = str(langcodes.find(origin_s))
            except LookupError:
                languages[origin_s] += 1
                if debug:
                    click.secho(f'Skipping unknown origin language {origin_s}', fg='yellow')
                warning = True

    if not warning and not info:
        click.secho(f'Unknown category format {cat_name}', fg='yellow')
    return info


def parse_categories(db, name_id, debug=False):
    results = collections.defaultdict(set)
    for cat_name in db.lookup_all('name',
                                  'category_membership LEFT JOIN categories ON category_id==id',
                                  {'name_id': name_id}):
        info = parse_category(cat_name, debug=debug)
        for k, v in info.items():
            results[k].add(v)
    return dict(results)


def parse_macro(template, param_names, debug=False):
    d = {}
    if debug:
        click.secho(str(template), fg='cyan')
    for param in template.params:
        try:
            param_number = int(str(param.name))
            name = param_names[param_number]
        except ValueError:
            name = str(param.name).strip()

        m = TRAILING_NUMBER.match(name)
        if m:
            name = m.group(1)
        name = f'{str(template.name).replace(" ", "-")}.{name}'

        value = str(param.value)
        if '{' in value or '[' in value:
            if debug:
                click.secho(f'Wikicode in Template: {value} ({name})', fg='yellow')
            continue

        if name == 'given-name.from':
            if '<' in value or ':' in value:
                if debug:
                    click.secho(f'Given from name: {value}', fg='blue')
                continue

            try:
                value = str(langcodes.find(value))
            except LookupError:
                languages[value] += 1
                if debug:
                    click.secho(f'Skipping unknown "from" language {value}', fg='yellow')
                continue

        if name not in d:
            d[name] = set()
        d[name].add(value)
    return d


def parse_wiki(name, wiki_text, debug=False):
    info = {}
    hit = False
    wikicode = mwparserfromhell.parse(wiki_text)
    for template in wikicode.filter_templates():
        template_name = str(template.name)
        if template_name not in TEMPLATE_ARGS:
            continue
        hit = True
        d = parse_macro(template, TEMPLATE_ARGS[template_name], debug=debug)
        merge_dict(info, d)

    if not hit:
        if debug:
            click.secho(f'Pattern miss: {name}')
        return info

    return info


def parse_name(db, name_id, name, wiki_text, debug=False):
    categories = parse_categories(db, name_id, debug=debug)
    if categories:
        stats['categories'] += 1
    if debug:
        click.secho(f'Category Result: {categories}', bg='blue')

    info = parse_wiki(name, wiki_text, debug=debug)
    if info:
        stats['pages'] += 1
    if debug:
        click.secho(f'Wiki Result: {info}', bg='blue')

    merge_dict(info, categories)
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name', nargs='?')
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()

    errors = collections.Counter()

    name_query = 'SELECT id, name, wiki_text FROM names WHERE wiki_text IS NOT NULL'
    if args.name:
        name_query += f' AND name == "{args.name}"'
    else:
        name_query += ' ORDER BY name'

    try:
        with WiktionaryDB() as db:
            names = list(db.query(name_query))
            for name_d in tqdm(names):
                try:
                    parsed_info = parse_name(db, name_d['id'], name_d['name'], name_d['wiki_text'],
                                             debug=args.name is not None or args.debug)
                    gender_flag = 0
                    for key, value in parsed_info.items():
                        src, field = key.split('.')
                        if field in ['lang', 'origin']:
                            for lang in value:
                                db.unique_insert(f'name_{field}', {'name_id': name_d['id'], 'lang': lang})
                        elif field in ['eq', 'var', 'dim', 'diminutive', 'varform']:
                            rel = Relationship.lookup(field)
                            entry = {
                                'name_id': name_d['id'],
                                'relationship': rel,
                            }
                            for other_name in value:
                                if other_name == name_d['name']:
                                    continue
                                entry['name_id2'] = db.lookup('id', 'names', {'name': other_name})
                                if not entry['name_id2']:
                                    continue
                                db.unique_insert('relationships', entry)
                        elif field == 'gender':
                            for gender_s in value:
                                gender_f = GenderFlag[gender_s.upper()]
                                gender_flag |= gender_f
                        else:
                            raise RuntimeError(f'Unable to process field: {field}')

                        name_info = {'id': name_d['id'], 'last_parse': datetime.datetime.now(),
                                     'gender_flag': gender_flag}
                        db.update('name_info', name_info)
                except Exception as e:
                    if isinstance(e, NotImplementedError):
                        raise e
                    errors[str(e), str(type(e))] += 1
    finally:
        for k, v in languages.most_common():
            click.secho(f'{v:4d} {k}', bg='blue')
        for k, v in errors.most_common():
            click.secho(f'{v:4d} {k}', bg='yellow', fg='black')
        for key, c in stats.items():
            click.secho(f'Parsed {key} for {c}/{len(names)} names ({c*100/len(names):.2f}%)', fg='blue')
