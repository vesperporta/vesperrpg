"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence
Email: vesper.porta@protonmail.com

Load and parse a CSV file.
This whole file is expected to be replaced with database management.

# TODO: Post MVP. Change to database management classes.
"""

import os
from os.path import isfile, join

from models import rpg_const, Stat, StatType, StatGroup, BodyPart


data_path = 'datasheets/'
data_extension = '.csv'
data_relationships = {
    'Public': [
        'Humble', 'Extroverted', 'Thrifty', 'Stressed', 'Depressed',
        'Psychotic',
    ],
}


def load_default_data():
    rpg_const.INFO = {
        'stats': {
            'headers': None,
            'name': 'Stat',
            'plural': 'Stats',
            'description': 'Body and soul unifying statistics.',
            'base_value': 1,
        },
        'disciplines': {
            'headers': None,
            'name': 'Discipline',
            'plural': 'Disciplines',
            'description': 'Key indicators of a character.',
            'base_value': 1,
        },
        'skills': {
            'headers': None,
            'name': 'Skill',
            'plural': 'Skills',
            'description': 'Skills learned through life.',
            'base_value': 1,
        },
        'abilities': {
            'headers': None,
            'name': 'Ability',
            'plural': 'Abilities',
            'description': 'Regular activities performed by a character.',
            'base_value': 0,
        },
        'species': {
            'headers': None,
            'name': 'Species',
            'plural': 'Species',
            'description': 'Type of character builds for the differing species.',
            'base_value': 0,
        },
        'effects': {
            'headers': None,
            'name': 'Effect',
            'plural': 'Effects',
            'description': 'Building blocks to create anything.',
            'base_value': 0,
        },
        'disorders': {
            'headers': None,
            'name': 'Disorder',
            'plural': 'Disorders',
            'description': 'Psychological traits undesirable from normal.',
            'base_value': 0,
        },
        'phobias': {
            'headers': None,
            'name': 'Phobia',
            'plural': 'Phobias',
            'description': 'Fears of a character.',
            'base_value': 0,
        },
    }


def load_education():
    rpg_const.RATINGS = {}
    rpg_const.RELATIONS = {}
    rpg_const.RATINGS['Primary'] = load_stat_csv('social-activities-primary')
    rpg_const.RATINGS['Further'] = load_stat_csv('social-activities')
    rpg_const.RELATIONS['Primary'] = load_stat_csv('edu-primary-relationships')
    rpg_const.RELATIONS['Further'] = load_stat_csv('edu-further-relationships')
    rpg_const.TEACHINGS = load_stat_csv('teachings')


def _get_file(name):
    os.chdir(os.path.dirname(__file__))
    path = join(os.getcwd(), data_path, '{}{}'.format(name, data_extension))
    if not isfile(path):
        raise Exception('Failed to find data source. path={}'.format(path))
    file = open(path, encoding='UTF-8')
    return file


def _str_to_float(value):
    try:
        return float(value)
    except ValueError:
        pass
    try:
        return int(value)
    except ValueError:
        pass
    return value


def _define_row_data_in_object(row, headers, class_definition=None):
    if not row:
        return None
    kay_value_ids = ['cross', 'affect', 'spread', 'draw', ]
    skip_ids = ['mult', 'value', ]
    rtn = class_definition() if class_definition else Stat()
    index = -1
    for key in headers:
        index += 1
        key_low = key.lower().replace(' ', '_')
        value = row[index]
        if not value or key_low in skip_ids:
            continue
        if '|' in value:
            value = value.split('|')
        if key_low in ['type']:
            # Race type required for this value
            value = StatType(name=value)
        if key_low in ['group']:
            # Race type required for this value
            value = StatGroup(name=value)
        if key_low in kay_value_ids:
            value = getattr(rtn, key_low) or []
            if row[index]:
                value.append(
                    StatType(row[index], ratio=_str_to_float(row[index + 1])))
        if not hasattr(rtn, key_low):
            rtn.unknown[key] = value
        setattr(rtn, key_low, value)
    return rtn


def load_stat_csv(name, row_data=False, group=None):
    file = _get_file(name)
    index = -1
    try:
        info = rpg_const.INFO[name]
    except KeyError:
        info = {
            'name': name, 'plural': name, 'description': '', 'base_value': 0,
            'headers': [],
        }
        rpg_const.INFO[name] = info
    if not group:
        group = StatGroup(
            name=info['plural'],
            description=info['description'],
            base_value=info['base_value'],
        )
    stats = []
    try:
        for line in file:
            index += 1
            row = line.replace('\n', '').split(',')
            if not row[0]:
                continue
            if index == 0:
                info['headers'] = row
                continue
            if row_data:
                stats.append(row)
                continue
            stat = _define_row_data_in_object(row, info['headers'])
            if not stat.group:
                stat.group = group
            stats.append(stat)
    except UnicodeDecodeError as error:
        print(error)
    group.stats = stats
    return group if not row_data else stats


def _search_many_csv_file(search, search_column='Group', filename='effects'):
    file = _get_file(filename)
    index = -1
    search_index = -1
    headers = None
    rtn = []
    try:
        for line in file:
            index += 1
            row = line.replace('\n', '').split(',')
            if not row[0]:
                continue
            if index == 0:
                headers = row
                search_index = headers.index(search_column)
                continue
            if row[search_index] == search:
                rtn.append(row)
    except UnicodeDecodeError as error:
        print(error)
    return rtn, headers


def _search_csv_file(search, filename='effects'):
    file = _get_file(filename)
    index = -1
    name_index = -1
    headers = None
    try:
        for line in file:
            index += 1
            row = line.replace('\n', '').split(',')
            if not row[0]:
                continue
            if index == 0:
                headers = row
                name_index = headers.index('Name')
                continue
            if row[name_index] == search:
                return row, headers
    except UnicodeDecodeError as error:
        print(error)
    return None, headers


def search_effect_many(
        search, search_column='Group', cache=False, class_definition=None
):
    class_definition = class_definition if class_definition else BodyPart
    search_id = '{}_{}'.format(search, search_column)
    if cache and search_id in rpg_const.CACHE.keys():
        return rpg_const.CACHE[search_id]
    rows, headers = _search_many_csv_file(search, search_column=search_column)
    rtn = []
    for row in rows:
        part = _define_row_data_in_object(row, headers, class_definition)
        if cache:
            rpg_const.CACHE[part.name] = part
        rtn.append(part)
    if cache:
        rpg_const.CACHE[search_id] = rtn
    return rtn


def search_effect(search, cache=False):
    if cache and search in rpg_const.CACHE.keys():
        return rpg_const.CACHE[search]
    row, headers = _search_csv_file(search)
    part = _define_row_data_in_object(row, headers, BodyPart)
    if cache:
        rpg_const.CACHE[part.name] = part
    return part
