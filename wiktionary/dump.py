from . import WiktionaryDB
from buckets import get_bucket
import click
import pathlib
import yaml

ROOT = pathlib.Path('data/')
ROOT.mkdir(exist_ok=True)

seen = set()


def to_yaml_dict(d):
    new_d = {}
    for name, value in d.items():
        if isinstance(value, set):
            new_d[name] = sorted(value)
        elif isinstance(value, dict):
            new_d[name] = to_yaml_dict(value)
        else:
            new_d[name] = value
    return new_d


def main():
    db = WiktionaryDB()
    db.update_database_structure()
    current_bucket = None
    current_path = None
    current_data = None

    name_lookup = db.dict_lookup('id', 'name', 'names')

    try:
        for name_d in db.query('SELECT * FROM names LEFT JOIN name_info ON names.id == name_info.id'
                               ' WHERE wiki_text IS NOT NULL ORDER BY name COLLATE NOCASE ASC'):
            name = name_d['name']
            name_id = name_d['id']
            bucket = get_bucket(name)

            if bucket != current_bucket:
                if current_data is not None:
                    yaml.safe_dump(to_yaml_dict(current_data), open(current_path, 'w'), allow_unicode=True)
                current_bucket = bucket
                bucket_s = ' '.join(bucket)
                click.secho('Switching to ', nl=False)
                click.secho(f'{bucket_s:20}', nl=False, fg='bright_blue')
                click.secho(f' ({name})')
                current_path = ROOT / ('_'.join(bucket) + '.yaml')
                if current_path.exists():
                    current_data = yaml.safe_load(open(current_path))
                else:
                    current_data = {}

            if name not in current_data:
                current_data[name] = {}

            entry = current_data[name]

            # Convert lists to set
            for field in entry:
                if isinstance(entry[field], list):
                    entry[field] = set(entry[field])

            name_d = dict(name_d)

            if name_d.get('gender_flag'):
                entry['gender_flag'] = entry.get('gender_flag', 0) | name_d['gender_flag']

            for rel in db.query(f'SELECT relationship, name_id2 FROM relationships WHERE name_id={name_id}'):
                key = rel['relationship'].name.lower()
                if key not in entry:
                    entry[key] = set()
                entry[key].add(name_lookup[rel['name_id2']])
            for field in ['lang', 'origin']:
                for lang in db.lookup_all('lang', f'name_{field}', {'name_id': name_id}):
                    if field not in entry:
                        entry[field] = set()
                    entry[field].add(lang)
    finally:
        if current_data is not None:
            yaml.safe_dump(to_yaml_dict(current_data), open(current_path, 'w'), allow_unicode=True)
