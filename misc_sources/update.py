import argparse
import pathlib
import requests
import click
import yaml

from buckets import get_bucket

SOURCES = {
    'brianary': 'https://raw.githubusercontent.com/brianary/Lingua-EN-Nickname/main/nicknames.txt',
    'carltonnorthern': 'https://raw.githubusercontent.com/carltonnorthern/nicknames/master/names.csv',
    'hajongler': ['https://raw.githubusercontent.com/HaJongler/diminutives.db/master/male_diminutives.csv',
                  'https://raw.githubusercontent.com/HaJongler/diminutives.db/master/female_diminutives.csv'],
    'meranda': 'https://web.archive.org/web/20181022154748/https://deron.meranda.us/data/nicknames.txt',
    'onyxrev': 'https://raw.githubusercontent.com/onyxrev/common_nickname_csv/master/nicknames.csv',
    'mrcsabatoth': 'https://raw.githubusercontent.com/MrCsabaToth/SOEMPI/master/openempi/conf/name_to_nick.csv',
}

CACHE_FOLDER = pathlib.Path('misc_sources/cache')
ROOT = pathlib.Path('data/')
ROOT.mkdir(exist_ok=True)


def download(redownload=False):
    raw_files = []
    for name, urldata in SOURCES.items():
        src_folder = CACHE_FOLDER / name
        src_folder.mkdir(exist_ok=True)
        if isinstance(urldata, str):
            urls = [urldata]
        else:
            urls = urldata
        for url in urls:
            filename = url.split('/')[-1]
            filepath = src_folder / filename
            raw_files.append((name, filepath))
            if filepath.exists() and not redownload:
                continue
            click.secho(f'Downloading {url}...', fg='blue')
            req = requests.get(url)
            with open(filepath, 'w') as f:
                f.write(req.text)
    return raw_files


def parse_to_common(raw_files):
    common = {}
    for src, path in raw_files:
        if src not in common:
            common[src] = {}

        def add_nick(name, nick, key='is_short_for'):
            if nick not in common[src]:
                common[src][nick] = {}
            if key not in common[src][nick]:
                common[src][nick][key] = []
            if name not in common[src][nick][key]:
                common[src][nick][key].append(name)

        def add_gender(name, gender_flag, key='gender_flag'):
            if name not in common[src]:
                common[src][name] = {}
            if key not in common[src][name]:
                common[src][name][key] = 0
            common[src][name][key] |= gender_flag

        if src == 'brianary':
            for line in open(path).readlines():
                pieces = line.strip().split('\t')
                name = pieces[0]
                nicks = pieces[1].split(' ')
                for nick in nicks:
                    if nick.endswith('E'):
                        # https://github.com/brianary/Lingua-EN-Nickname/blob/07258c7d401fb3eb03af373c2a6f86c31f0b2cfd/Nickname.pm#L142
                        root = nick[:-1]
                        for ending in ['i', 'ie', 'ey', 'y']:
                            if name == root + ending:
                                continue
                            add_nick(name, f'{root}{ending}')
                    else:
                        add_nick(name, nick)
        elif src == 'carltonnorthern':
            for line in open(path).readlines():
                pieces = line.strip().split(',')
                name = pieces[0].title()
                nicks = pieces[1:]
                for nick in nicks:
                    nick = nick.title()
                    add_nick(name, nick)
        elif src == 'hajongler':
            gender_s = path.name.split('_')[0]
            if gender_s == 'female':
                gender_flag = 1
            else:
                gender_flag = 2
            for line in open(path).readlines():
                pieces = line.strip().split(',')
                name = pieces[0]
                nicks = pieces[1:]
                add_gender(name, gender_flag)
                for nick in nicks:
                    add_gender(nick, gender_flag)
                    add_nick(name, nick)
        elif src == 'meranda':
            for line in open(path).readlines():
                if line[0] == '#':
                    continue
                # Special case due to bad formatting
                line = line.replace('  GEORGINE        0', '\tGEORGINE\t0')

                pieces = line.strip().lower().replace('\t\t', '\t').split('\t')
                if len(pieces) != 3:
                    click.secho(repr(line), fg='red')
                    continue
                nick = pieces[0].title()
                name = pieces[1].title()
                add_nick(name, nick)
        elif src == 'mrcsabatoth':
            for line in open(path).readlines():
                if line.startswith('firstname'):
                    continue
                pieces = line.strip().title().split(',')
                name = pieces[0]
                nicks = pieces[1:]
                for nick in nicks:
                    add_nick(name, nick)
        elif src == 'onyxrev':
            for line in open(path).readlines():
                if line.startswith('id,'):
                    continue
                pieces = list(map(str.strip, line.title().split(',')))
                name = pieces[1]
                nick = pieces[2]
                if name == nick:
                    continue
                add_nick(name, nick)
        else:
            click.secho(f'Skipping {src}', fg='yellow')

    for src, data in common.items():
        fn = CACHE_FOLDER / src / 'common.yaml'
        yaml.dump(data, open(fn, 'w'))

    return common


def integrate(common):
    all_names = set()
    for src, data in common.items():
        all_names = all_names.union(set(data.keys()))

    current_bucket = None
    current_path = None
    current_data = None
    for name in sorted(all_names):
        bucket = get_bucket(name)
        if bucket != current_bucket:
            if current_data is not None:
                yaml.safe_dump(current_data, open(current_path, 'w'), allow_unicode=True)
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

        for src, data in common.items():
            if name not in data:
                continue
            ndata = data[name]
            for k, v in ndata.items():
                if k not in current_data[name]:
                    current_data[name][k] = v
                elif k == 'gender_mask':
                    current_data[name][k] |= v

    if current_data is not None:
        yaml.safe_dump(current_data, open(current_path, 'w'), allow_unicode=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--redownload', action='store_true')
    args = parser.parse_args()

    raw_files = download(args.redownload)
    common = parse_to_common(raw_files)
    integrate(common)
