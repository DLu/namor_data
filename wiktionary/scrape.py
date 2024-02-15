import argparse
import click
import datetime
from tqdm import tqdm

from . import WiktionaryDB

# NB: pwiki imports are done inside methods to ensure only scraping is done in python3.9


CAT_PREFIX = 'Category:'
ROOT_CATEGORY = CAT_PREFIX + 'Given_names_by_language'


def crawl_category(db, wiki, category_d):
    from pwiki.gquery import GQuery
    cat_id = category_d['id']
    cat_name = category_d['name']
    bar = tqdm(total=wiki.category_size(cat_name))
    for member_array in GQuery.category_members(wiki, cat_name):
        page_name = member_array[0]
        bar.set_description(f'{page_name:40}')
        if page_name.startswith(CAT_PREFIX):
            db.unique_insert('categories', {'name': page_name})
        elif ':' in page_name:
            click.secho(f'Ignoring special page {page_name}', fg='yellow')
        else:
            name_id = db.unique_insert('names', {'name': page_name})
            db.unique_insert('category_membership', {'category_id': cat_id, 'name_id': name_id})

        bar.update()
    db.update('categories', {'id': cat_id, 'last_crawl': datetime.datetime.now()})


def crawl_name_page(db, wiki, name_d):
    name_d['wiki_text'] = wiki.page_text(name_d['name'])
    name_d['last_crawl'] = datetime.datetime.now()
    db.update('names', name_d)


def main():
    from pwiki.wiki import Wiki

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--recrawl-categories', action='store_true')
    parser.add_argument('-p', '--recrawl-pages', action='store_true')
    args = parser.parse_args()

    wiki = Wiki('en.wiktionary.org')

    sixty_days_ago = datetime.datetime.now() - datetime.timedelta(days=60)

    with WiktionaryDB() as db:
        if db.count('categories') == 0:
            db.insert('categories', {'name': ROOT_CATEGORY})

        cat_query = 'SELECT * FROM categories WHERE last_crawl IS NULL'
        if args.recrawl_categories:
            cat_query += f' OR last_crawl < "{sixty_days_ago}"'

        queue = list(db.query(cat_query))

        bar = tqdm(queue)
        for category_d in bar:
            bar.set_description(category_d['name'])
            crawl_category(db, wiki, category_d)

        name_query = 'SELECT id, name FROM names WHERE wiki_text IS NULL'
        if args.recrawl_pages:
            name_query += f' OR (last_crawl IS NULL OR last_crawl < "{sixty_days_ago}")'
        name_query += ' ORDER BY name'
        names = list(db.query(name_query))
        bar = tqdm(names)
        for name_d in bar:
            bar.set_description(f"{name_d['name']:20}")
            crawl_name_page(db, wiki, dict(name_d))
