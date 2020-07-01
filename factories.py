"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence
Email: vesper.porta@protonmail.com

Factories for various parts of the Vesper RPG.
All methods should be housed in factory classes where each context of the build
can be separated into sections: creation of items, creation of life stages.

# TODO: Post MVP. clean up lose methods into factory classes.
"""

from random import choice, choices, random, sample

from load_data import (
    load_stat_csv, search_effect, load_default_data, load_education
)
from models import *
from models import ItemContainer, PsychePivot
from rpg_util import duplicate_object


def load_game_data():
    """
    Load required data upfront into memory as a way to process the rest of the
    application, this is not desired production management of memory or
    resources and expected to be replaced with a database and other data
    management classes.
    """
    load_default_data()
    rpg_const.CLASSES = load_stat_csv('skill-classes')
    rpg_const.STATS = load_stat_csv('stats')
    rpg_const.DISCIPLINES = load_stat_csv('disciplines')
    rpg_const.SKILLS = load_stat_csv('skills')
    # Trading on the skill being used for an item not the item: killing
    rpg_const.LICENSES_TRADE = [
        s for s in rpg_const.SKILLS.stats if int(s.license_trade) == 1]
    rpg_const.LICENSES_ACT = [
        s for s in rpg_const.SKILLS.stats if int(s.license_act) == 1]
    rpg_const.ABILITIES = load_stat_csv('abilities')
    rpg_const.DISORDERS = load_stat_csv('disorders')
    rpg_const.PHOBIAS = load_stat_csv('phobias')
    rpg_const.LICENSES = load_stat_csv('licenses')
    rpg_const.DAMAGE = load_stat_csv('damage')
    rpg_const.DAMAGE_HEALTH = [
        d.name for d in rpg_const.DAMAGE.stats
        if int(d.unknown['Health']) == 1
    ]
    rpg_const.DAMAGE_INDICATORS = [
        d.name for d in rpg_const.DAMAGE.stats
        if int(d.unknown['Indicator']) == 1
    ]
    rpg_const.DAMAGE_MODIFIERS = [
        d.name for d in rpg_const.DAMAGE.stats
        if int(d.unknown['Modifier']) == 1
    ]
    rpg_const.DAMAGE_FUNCTIONS = [
        d.name for d in rpg_const.DAMAGE.stats
        if int(d.unknown['Function']) == 1
    ]
    rpg_const.DAMAGE_CRIMINAL = [
        d for d in rpg_const.DAMAGE.stats
        if float(d.unknown['Criminal']) > 0
    ]
    rpg_const.SPECIES = load_stat_csv('species')
    rpg_const.SOCIAL_EMOTIONS = load_stat_csv('social-emotions')
    rpg_const.SOCIAL_ACTIVITIES = load_stat_csv('social-activities')
    rpg_const.SOCIAL_ACTIVITIES_PRIMARY = load_stat_csv(
        'social-activities-primary')
    create_species()
    create_locations()
    load_education()


def create_locations():
    locations = {
        'Inner City': {
            'long_name': 'Inner Los Angeles, Earth',
            'planet': 'Earth',
            'solar_system': 'Milky Way',
            'income_percentiles': [0, 98353, 133392, 159955, 187102, 216174,
                                   243987, 280021, 331821, 410977],
            'age_distribution': [7, 7, 15, 20, 16, 11, 9, 8, 6, 1],
            'death_distribution': [0.5, 1.5, 1, 1, 2, 2, 10, 19, 30, 33],
            'wealth': 4,
            'movement': 1,
            'crime': 6,
            'religion': 'Neo-Buddhist',
        }
    }
    for name in locations.keys():
        location = LifeLocation(name=name)
        for detail in locations[name].keys():
            if locations[name][detail]:
                setattr(location, detail, locations[name][detail])
        rpg_const.LOCATIONS.append(location)


def _define_body_part(obj):
    """Recurse through the definition of an object item and build structure."""
    index = -1
    replaces = None
    if type(obj.connections) is not list:
        obj.connections = [obj.connections]
    if obj.affect:
        replaces = [a.ratio for a in obj.affect if a.name == 'Replaces']
    if replaces:
        replaces = replaces[0]
        _generated_body_parts.append(replaces)
    for connection in obj.connections:
        index += 1
        child_part = build_object_item(connection, obj)
        if child_part:
            obj.connections[index] = child_part
            child_con = child_part.connections
            if replaces in child_con:
                child_con[child_con.index(replaces)] = obj
            elif obj.name in child_con:
                child_con[child_con.index(obj.name)] = obj
    if len(obj.functions) > 0:
        if type(obj.functions) is not list:
            obj.functions = [obj.functions]
        stat_functions = []
        for func in obj.functions:
            ratio = float(func[func.index(':') + 1:]) if ':' in func else 1
            name = func[:func.index(':')] if ':' in func else func
            stat_functions.append(StatType(name=name, ratio=ratio))
        obj.functions = stat_functions
    if int(obj.contain_quantity) > 0 or float(obj.contain_volume) > 0 or \
            obj.contain_restrictions:
        if type(obj.contain_restrictions) is str:
            obj.contain_restrictions = [obj.contain_restrictions]
        contents = obj.contains or []
        obj.contains = ItemContainer(parent=obj)
        obj.contains.max_weight = float(obj.contain_weight)
        obj.contains.max_volume = float(obj.contain_volume)
        obj.contains.quantity_max = int(obj.contain_quantity)
        restrict = []
        type_maxes = {}
        for r in obj.contain_restrictions:
            value = r
            if '*' in r:
                value = r[:r.index('*')]
                type_maxes.update({value: int(r[r.index('*') + 1:])})
            restrict.append(value)
        obj.contains.restrict = restrict
        obj.contains.q_max_type = type_maxes
        if type(contents) is str:
            contents = [contents]
        for c in contents:
            c = build_object_item(c)
            if c:
                obj.contains.add(c)
    if int(obj.wear_quantity) > 0 or float(obj.wear_volume) > 0 or \
            obj.wear_restrictions:
        if type(obj.wear_restrictions) is str:
            obj.wear_restrictions = [obj.wear_restrictions]
        contents = obj.wears or []
        obj.wears = ItemContainer(parent=obj)
        obj.wears.max_weight = float(obj.wear_weight)
        obj.wears.max_volume = float(obj.wear_volume)
        obj.wears.quantity_max = int(obj.wear_quantity)
        restrict = []
        type_maxes = {}
        for r in obj.wear_restrictions:
            value = r
            if '*' in r:
                value = r[:r.index('*')]
                type_maxes.update({value: int(r[r.index('*') + 1:])})
            restrict.append(value)
        obj.wears.restrict = restrict
        obj.wears.q_max_type = type_maxes
        if type(contents) is str:
            contents = [contents]
        for c in contents:
            c = build_object_item(c)
            if c:
                obj.wears.add(c)
    return obj


_generated_body_parts = []


def build_object_item(part_id, parent=None, raw_part=None):
    """
    Build an item for use within the RPG.
    The structure is built to efficiently identify a path to the actioning
    part of the object when action is applied.

    :param part_id: The name of the base part of an object.
    :param parent: Optional definition for the heirarchy for this body part.
    :return: BodyPart
    """
    quantity = 1
    if '*' in part_id:
        quantity = int(part_id[part_id.index('*') + 1:])
        part_id = part_id[:part_id.index('*')]
    if not raw_part:
        if part_id in _generated_body_parts:
            return None
        _generated_body_parts.append(part_id)
        body_part = search_effect(part_id)
    else:
        body_part = raw_part
    if not body_part:
        return None
    _define_body_part(body_part)
    if quantity > 1:
        body_part.quantity = int(quantity)
    body_part.parent = parent
    if not parent:
        _generated_body_parts.clear()
    return body_part


def create_character_body(character):
    """
    Create a structure to link all parts of a body for a character together.
    This method will override any current structure of a character if present.

    :param character: The character to update with a new body structure.
    """
    species = duplicate_object(choice(rpg_species))
    character.body.species = species
    character.stats.base_value = species.stats_base
    character.disciplines.base_value = species.disciplines_base
    character.skills.base_value = species.skills_base
    sex = choices(species.genders, weights=species.genders_spread)[0]
    character.body.gender = sex
    body_id = '{} {}'.format(species.name, sex.name)
    character.body.whole = build_object_item(body_id)
    brain_id = '{} Brain'.format(species.name, sex.name)
    character.body.brain = character.body.whole.find_name(brain_id)[0]
    # TODO: Androids would require a manufacturers id outside of the self.
    character.body.whole.manufacturer = character


def create_species():
    """
    Generates the understanding for types of species available in game.
    Each species should have their own layout for life stages.
    HACK: MVP Short Cuts.
    """
    default_stages = [
        LifeStage(name='Early', age_from=0, age_to=5, expected=[
            StatType(name='Home', description='Family', ratio=1),
            StatType(name='Home', description='Religion', ratio=0.9),
        ]),
        LifeStage(name='Primary', age_from=6, age_to=18, expected=[
            StatType(name='Home', description='Family', ratio=0.99),
            StatType(name='Home', description='Religion', ratio=0.7),
            StatType(name='Home', description='Hobby', ratio=0.2),
            StatType(name='School', description='Primary', ratio=0.95),
            StatType(name='School', description='Secondary', ratio=0.95),
        ]),
        LifeStage(name='Further', age_from=19, age_to=21, expected=[
            StatType(name='Home', description='Family', ratio=0.96),
            StatType(name='Home', description='Religion', ratio=0.4),
            StatType(name='Home', description='Hobby', ratio=0.6),
            StatType(name='School', description='Further', ratio=0.7),
            StatType(name='Job', description='', ratio=0.1),
        ]),
        LifeStage(name='Work', age_from=22, age_to=1000, expected=[
            StatType(name='Home', description='Family', ratio=0.96),
            StatType(name='Home', description='Religion', ratio=0.2),
            StatType(name='Home', description='Hobby', ratio=0.2),
            StatType(name='Job', description='', ratio=0.6),
        ]),
    ]
    for s in rpg_const.SPECIES.stats:
        species = RpgSpecies(
            name=s.name,
            description=s.description,
            species_type=s.type,
            stages=[duplicate_object(n) for n in default_stages]
        )
        for g in s.unknown['Genders']:
            id = '{} {}'.format(s.name, g)
            species.genders.append(RpgSpeciesGender(g, id, s.name))
        species.genders_spread = [float(g) for g in s.unknown['Genders Spread']]
        species.sexualities = s.unknown['Sexualities']
        species.sexualities_spread = [
            float(g) for g in s.unknown['Sexualities Spread']]
        rpg_species.append(species)


def create_character_stats(character):
    """
    Generate a new stats for a new body.
    Soul stats persist from body to body.
    """
    character.stats = duplicate_object(rpg_const.STATS)
    fresh = character.stats.stats
    character.stats.stats = []
    if not character.stats_soul:
        character.stats_soul = StatGroup(
            name='Soul',
            description='Divined marks of truth reading a characters soul.',
            base_value=1,
            stats=[
                s for s in fresh if s.unknown['Part'] == 'Soul'
            ],
        )
    character.stats.stats += character.stats_soul.stats
    if character.body:
        character.body.stats = StatGroup(
            name='Body',
            description='Statistics form from the physical body',
            base_value=1,
            stats=[
                s for s in fresh if s.unknown['Part'] != 'Soul'
            ],
        )
        character.stats.stats += character.body.stats.stats


def _find_income_percentile(location, income):
    index = -1
    rtn = 0
    for i in location.income_percentiles:
        index += 1
        if i < income:
            rtn = index
    return rtn * 10


def _define_choices_spread(peak, list_selection, spread=4):
    weights = []
    length = len(list_selection)
    index = -1
    while index < length - 1:
        index += 1
        distance = peak - index if index < peak else index - peak
        if distance > spread:
            value = 0.1
        else:
            value = float(0.2 * (spread - distance)) or 0.1
        weights.append(value)
    return weights


def _define_relationships(stage_type, age_from):
    relations = duplicate_object(rpg_const.RELATIONS[stage_type], deep=True)
    spread_type = 'Basic'
    if age_from > 21:
        spread_type = 'Advanced'
    elif age_from > 18:
        spread_type = 'Middle'
    rtn = StatGroup(name='Relationships', description='{}:{}'.format(
        stage_type, spread_type,
    ))
    for relation in relations.stats:
        spread_value = int(
            [s.ratio for s in relation.spread if s.name == spread_type][0])
        index = 0
        stat = Stat(name=relation.name)
        while index < spread_value:
            index += 1
            spread_random = sum([random()] * spread_value) / spread_value
            # TODO: Check for increased difficulty the closer index is to spread_value, Post MVP
            if spread_random > 0.5:
                stat.total += 1
                stat.ratio += (spread_random - 0.5) * 2
        rtn.stats.append(stat)
    return rtn


def _create_life_block(life_stage, block):
    follow_expected = random() < block.ratio
    edu = EducationStat()
    edu.duration_years = life_stage.age_to - life_stage.age_from
    edu.location = choices(
        rpg_const.LOCATIONS,
        weights=_define_choices_spread(0, rpg_const.LOCATIONS)
    )[0]
    edu.income = life_stage.expenses
    edu.teachings = [
        t for t in rpg_const.TEACHINGS.stats
        if t.name == 'Per Year'] * edu.duration_years
    teaching_name = 'Primary'
    if block.name == 'Job':
        pass
    if block.name == 'School':
        teaching_name = 'School'
        school_names = []
        if block.description in ['Primary', 'Secondary', ]:
            edu.ratings = duplicate_object(
                rpg_const.RATINGS['Primary'], deep=True)
            edu.relationships = _define_relationships(
                'Primary', life_stage.age_from)
        if block.description in ['Primary', ]:
            school_names = ['Los Angeles Primary', 'St. Trinity\'s primary',
                            'John Burns Academy', 'Vesper Institute LA']
        if block.description in ['Secondary', ]:
            school_names = ['Los Angeles Secondary', 'John Burns Academy',
                            'Vesper Institute LA']
        if block.description in ['Further', ]:
            teaching_name = 'Further'
            school_names = ['Vesper University', 'MIT', 'LA Uni']
            edu.ratings = duplicate_object(
                rpg_const.RATINGS['Further'], deep=True)
            edu.relationships = _define_relationships(
                'Primary', life_stage.age_from)
        edu.name = choice(school_names)
        if not follow_expected:
            if block.description in ['Further', ]:
                edu.name = 'Biker Gang Name'
                block.name = 'Gang'
    if block.name == 'Home':
        edu.ratings = duplicate_object(rpg_const.RATINGS['Primary'], deep=True)
        edu.relationships = _define_relationships(
            'Further', life_stage.age_from)
        if block.description == 'Hobby':
            hobbies = ['Gym', 'Shooting', 'Equestrian', 'Clubbing', 'Reading',
                       'Fencing', 'Motor Racing', 'Climbing', 'Martial Art',
                       'Labs', 'Camping']
            if life_stage.decision in ['Automatic', 'Born', ]:
                hobbies = ['Equestrian', 'Clubbing', 'Reading', 'Fencing',
                           'Climbing', 'Martial Art', 'Labs', 'Camping']
            edu.name = choice(hobbies)
            edu.abode = 'Place'
            edu.position = 'Active'
            if not follow_expected:
                edu.name = 'Biker Gang Name'
                edu.position = 'Grunt'
                block.name = 'Gang'
        elif block.description == 'Religion':
            teaching_name = 'Religion'
            religions = ['Neo-Buddhist', 'Buddhist', 'Scientology', 'Hindu',
                         'Seikh', 'Judaism', 'Christianity', 'Jedi', 'Islam', ]
            edu.name = choices(
                religions,
                weights=_define_choices_spread(
                    religions.index(life_stage.location.religion), religions)
            )[0]
            edu.abode = 'Temple'
            if life_stage.decision in ['Automatic', 'Born', ]:
                edu.position = 'Follower'
            else:
                edu.position = 'Leader'
        else:
            edu.name = '{}\'s {}'.format(life_stage.character.name, block.name)
            edu.abode = choice(['House', 'Apartment', 'Flat', ])
            if life_stage.decision in ['Automatic', 'Born', ]:
                edu.position = 'Child'
    teachings = [
        t for t in rpg_const.TEACHINGS.stats if t.group.name == teaching_name]
    edu.teachings += sample(teachings, 1)
    edu.cross_mappings = StatGroup(name='Mapping')
    if edu.ratings:
        for r in edu.ratings.stats:
            r.total = 1
            r.ratio = 1
            for s in r.cross:
                found = edu.cross_mappings.find(s.name)
                stat = found or Stat(name=s.name)
                stat.total += r.total / (1 + r.ratio)
                if not found:
                    edu.cross_mappings.stats.append(stat)
    if edu.relationships:
        for r in edu.relationships.stats:
            r.total = 1
            r.ratio = 1
            for s in r.cross or []:
                found = edu.cross_mappings.find(s.name)
                stat = Stat(name=s.name)
                stat.total = r.total / (1 + r.ratio)
                if not found:
                    edu.cross_mappings.stats.append(stat)
    return edu if follow_expected and random() < block.ratio else None


def create_life_stage_eduction(life_stage, previous_stage):
    """
    Generate a set of home, education, and job parts to a life stage.

    :param life_stage: LifeStage defining model.
    :param previous_stage: LifeStage defining the previous model.
    """
    if previous_stage and type(previous_stage) is not list:
        life_stage.location = previous_stage.location
    if not life_stage.location:
        life_stage.location = choice(rpg_const.LOCATIONS)
    life_stage.expenses = choices(
        life_stage.location.income_percentiles,
        weights=_define_choices_spread(
            life_stage.location.wealth,
            life_stage.location.income_percentiles,
        ),
    )[0]
    life_stage.projected = choices(
        life_stage.location.income_percentiles,
        weights=_define_choices_spread(
            life_stage.location.wealth,
            life_stage.location.income_percentiles,
        ),
    )[0]
    if not previous_stage:
        life_stage.decision = 'Born'
    else:
        # TODO: How a character is meant to make a decision progress to
        pass
    for block in life_stage.expected:
        life_block = _create_life_block(life_stage, block)
        if life_block:
            life_stage.education.append(life_block)


def _find_activities_by_name(character, activities):
    rtn = []
    for stage in character.character.body.life_stages:
        # stage = LifeStage
        for edu in stage.education:
            # edu = EducationStat
            if not edu.ratings:
                continue
            rtn += [
                rate for rate in edu.ratings.stats
                if rate.name in activities
            ]
    return rtn


def _find_relationships_by_type(character, relationships):
    rtn = []
    for stage in character.character.body.life_stages:
        # stage = LifeStage
        for edu in stage.education:
            # edu = EducationStat
            if not edu.relationships:
                continue
            rtn += [
                rel for rel in edu.relationships.stats
                if rel.name in relationships
            ]
    return rtn


def convert_life_to_activities(character):
    """Convert a characters life_stages to social activities."""
    rtn = []
    for stat in rpg_const.SOCIAL_ACTIVITIES.stats:
        disorder = None
        if 'Disorder' in stat.unknown.keys():
            disorder = character.character.disorders.find(
                stat.unknown['Disorder'])
        activities_list = [stat.name]
        if 'Primary' in stat.unknown.keys():
            activities_list += [stat.unknown['Primary']]
        activities = _find_activities_by_name(character, activities_list)
        psyche_base = disorder.total if disorder else 0
        quantity = sum([r.total for r in activities]) or 1
        quality = sum([r.ratio for r in activities]) or 1
        log = PsychePivot(name=stat.name, type=StatType(name='Public'))
        log.rating = psyche_base + float(
            quantity /
            quality *
            sum([
                len(stage.education)
                for stage in character.character.body.life_stages
            ])
        )
        rtn.append(log)
    return rtn


def convert_life_to_social(character):
    """
    Convert a Characters life_stages to public and social statistics.
    """
    rtn = []
    for stat in rpg_const.SOCIAL_EMOTIONS.stats:
        disorder = None
        if 'Disorder' in stat.unknown.keys():
            disorder = character.character.disorders.find(
                stat.unknown['Disorder'])
        relationships = stat.unknown['Relationships']
        relationships = relationships.split('|') \
            if '|' in relationships else [relationships]
        relations = _find_relationships_by_type(character, relationships)
        log = PsychePivot(name=stat.name, type=StatType(name='Public'))
        psyche_base = disorder.total if disorder else 0
        quantity = sum([r.total for r in relations]) or 1
        quality = sum([r.ratio for r in relations]) or 1
        log.rating = psyche_base + float(
            quantity /
            quality *
            sum([
                len(stage.education)
                for stage in character.character.body.life_stages
            ])
        )
        rtn.append(log)
    return rtn
