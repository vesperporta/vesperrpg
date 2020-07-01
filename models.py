"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence
Email: vesper.porta@protonmail.com

Character sheet models for use in game modeling.
"""

from datetime import datetime

from rpg_util import duplicate_object, Middleware, hash_generate


class TypeConst:
    LISTS = [list, tuple, set, ]


class RpgConst:
    """
    Default constants expected throughout the game.

    Descriptions of some constants due to deviation from normal physics
    standards and the use of constants in the field.

    IMBUING_ENERGY_RATIO explanation:
    A bullet = 0.008KG = 718992352800000.0J
    A gun = 5KG = 449370220500000000.0J
    Example equation: item_energy * accustomed * IMBUING_ENERGY_RATIO
    To have too huge an effect for an imbuing would off balance a character and
    make the art form of imbuing strong or capable affects onto an item would
    render the effect ineffectual or too strong at a constant other than 0.002.
    """
    FPS_MAX = 60
    DEFAULT_TIME_UPDATE = 100
    TIME_RATIO = 0.04
    MASTERY_MILLISECONDS = 1000 * 60 * 60 * 10000 * 0.04
    FEEDBACK_MILLISECONDS = 1000 * 60 * 60 * 0.04
    STAT_EPIPHANY_RATIO = 0.05
    DISCIPLINE_EPIPHANY_RATIO = 0.5
    SKILL_EPIPHANY_RATIO = 1
    ENERGY_RATIO = 1
    MILLISECONDS = 1
    TIME_MASTERY = 1
    CIRCULATION_ZERO = 2
    DISTANCE_STEP = 0.01
    IMBUING_ENERGY_RATIO = 0.002
    SPECIES = []
    COMPANIES = []
    CLASSES = []
    REGISTERED_CLASSES = []
    STATS = []
    DISCIPLINES = []
    SKILLS = []
    ABILITIES = []
    DISORDERS = []
    PHOBIAS = []
    DAMAGE = []
    DAMAGE_HEALTH = []
    DAMAGE_MODIFIERS = []
    DAMAGE_FUNCTIONS = []
    DAMAGE_INDICATORS = []
    DAMAGE_CRIMINAL = []
    LICENSES = []
    LICENSES_TRADE = []
    LICENSES_ACT = []
    EFFECTS = []
    PLAYER = None
    TURN_BASED = False
    TURN_RATE_MIN = 500
    FRAME_RATE_MIN = 30
    CHARACTERS = []
    LOCATIONS = []
    SOCIAL_EMOTIONS = []
    SOCIAL_ACTIVITIES = []
    SOCIAL_ACTIVITIES_PRIMARY = []
    RELATIONS = {}
    RATINGS = {}
    TEACHINGS = {}
    INFO = {}
    GRAVITATIONAL_CONSTANT = 0.00000000000667408
    CACHE = {}
    EPIPHANY_RATIO = {
        'stats': 0.05,
        'disciplines': 0.5,
        'skills': 1,
    }
    EXPERIENCE_EXCHANGE = {
        'stats_skills': 2.7,
        'stats_disciplines': 1.7,
        'disciplines_skills': 2.1,
        'skills_stats': 0.8,
        'skills_disciplines': 0.7,
        'disciplines_stats': 0.6,
    }
    AVERAGE_KILO_VOLUME = 0.008
    TIME_STEP = 1000
    SEARCH_ACTIONS = ['Searching', 'Soul Divining']
    SEARCH_RATE = 13
    PERSONALISATION_LEVEL = 3
    CONVERSATION_DYNAMIC_LIMIT = 2
    CONVERSATION_DYNAMIC_MARKER = '#'
    YEAR_START_MINIMUM = 650
    YEAR_START_MODIFIER = 0
    VIOLATION_TIME = 1000 * 60 * 60 * 24 * 356
    GARBAGE_COLLECTION_FREQUENCY = 750
    MELEE_BLOCK_WAIT = 200
    JUMP_WAIT = 400
    GRENADE_ACCUSTOMED_THREASHOLD = 0.1
    TIME_ACTION_HOLSTER = 1500
    TIME_ACTION_UNHOLSTER = 3000
    TIME_ACTION_FUTURE_TACTITIAN = 2500
    TIME_ACTION_FOCUSING = 2000
    SYSTEM_ACTIVE = 1


class RpgDatetime(datetime):
    """
    Manage the datetime specific for the games translation of time in-game to
    real life and visa versa.

    TODO: Build out class to manage datetime conversion to in-game datetime.

    Expected format is unknown other than having the year reset to another Zero,
    thus the year 650LP as an example game year for Earth.

    Management of time on other planets is expected to be handled by keeping the
    year while changing the number of days and months to fit in the planets
    cycle around the respective star, modifying the month length to 10 is very
    acceptable along with the hours to become 20 instead of 24, minutes to 100,
    seconds to 100. For planets with axial rotation slower to the point of
    exceeding 10 months per year the days would just be spread evenly over the
    time.

    Earth:
    10 Months = 35.625 days to a month, February would be ginger month
    with awkward days: 356.25 - (36 * 9 = 324) = February = 32.25 days
    20 hours per day, 100 minutes per hour and 100 seconds per minute.
    Since my birthday is not a 'leap year' year:
    12th March 0LP at 18:33:33
    """
    YEAR_START = RpgConst.YEAR_START_MINIMUM


rpg_const = RpgConst()


class RpgTick(object):
    """
    Manage the chunk processing of objects known about within this system.

    # TODO: Required limiting on the number of chunks to process on each tick.
    # TODO: Monitoring options for a minimum tick rate per second is required.
    # TODO: For garbage collection will have to weak reference into this list.
    """
    KNOWN = []
    DIFF = 0
    LAST = 0
    CURRENT = 0

    _gc_count = -1

    @staticmethod
    def now():
        """Expected to be calculated only once per FPS."""
        return datetime.timestamp(datetime.now())

    @staticmethod
    def gc(self):
        """
        Garbage collection cycle for object specific garbage collection
        frequencies through the lifetime of this instance.

        It is optional to override this method.
        """
        pass

    @staticmethod
    def all_tock():
        """Manage the processing of all time related objects to process."""
        RpgTick.LAST = RpgTick.CURRENT
        if rpg_const.TURN_BASED:
            RpgTick.CURRENT += 1
        else:
            RpgTick.CURRENT = RpgTick.now()
        RpgTick.DIFF = RpgTick.CURRENT - RpgTick.LAST
        for n in RpgTick.KNOWN:
            if n._gc_count != -1:
                if n._gc_count > rpg_const.GARBAGE_COLLECTION_FREQUENCY:
                    n.gc()
                    n._gc_count = 0
                n._gc_count += 1
            n.tick()

    def tick(self):
        """
        Manages the FPS calculations expected from this model.

        It is required to override this method.

        :return: float difference between the last tick and now.
        """
        pass

    def __init__(self, *args, **kwargs):
        if not RpgTick.CURRENT:
            if rpg_const.TURN_BASED:
                RpgTick.CURRENT += 1
            else:
                RpgTick.CURRENT = RpgTick.now()
        RpgTick.LAST = RpgTick.CURRENT
        RpgTick.KNOWN.append(self)


class StatType:
    """Generic store for a type of data with a simple value associated."""
    _name = ''
    search = ''
    description = ''
    ratio = 0
    modifiers = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value or ''
        if not value:
            return
        if type(value) is list:
            value = ''.join(value)
        self.search = value.replace(' ', '').lower()

    @property
    def total(self):
        """Find the modified total of this StatType."""
        return self.ratio + sum([e.ratio for e in self.modifiers])

    def __init__(self, name=None, description='', ratio=1.0):
        self.name = name
        self.description = description
        self.ratio = ratio
        self.modifiers = []

    def __str__(self):
        return '<StatType "{}", total: {}>'.format(self.name, self.total)


class RpgSpeciesGender:
    """Species definition of a sex."""
    name = ''
    long = ''
    description = ''
    body = None

    def __init__(self, name='', long='', description='', body=None):
        self.name = name
        self.long = long
        self.description = description
        self.body = body

    def __str__(self):
        return ''.format(self.name)


class RpgSpecies:
    """Default object for a species definition."""
    type = ''
    bipedal = True
    name = ''
    description = ''
    stats_base = 1
    disciplines_base = 1
    skills_base = 1
    energy_base = 100
    concentration_base = 100
    fatigue_base = 100
    carry_by_weight = 0.3
    carry_by_strength = 0.7
    genders = None
    genders_spread = None
    sexualities = None
    sexualities_spread = None
    life_stages = None

    def __init__(self, name='', description='', species_type=None, stages=[]):
        self.name = name
        self.description = description
        self.type = species_type
        self.life_stages = stages
        self.genders = []
        self.genders_spread = []
        self.sexualities = []
        self.sexualities_spread = []
        self.life_stages = stages

    def __str__(self):
        return '{}'.format(self.name)


rpg_species = []


class Interaction:
    """Model interactions happening between two bodies."""
    character = None
    part = None
    item = None
    targets = None
    requires = None
    action = None
    action_frames = 0
    modifier = 0
    timing = 0
    control_timing = 0
    feedback_time = 0
    start = 0
    duration = 0
    distance_km = 0
    distance_ratio = None
    tracker = None
    medium = None
    accustomed = 0
    phobia_ratio = -1
    disorder_ratio = -1
    energy_draw = 0
    energy_ms = 0
    fatigue_draw = 0
    fatigue_ms = 0
    concentration_draw = 0
    concentration_ms = 0
    amount_draw = 0
    amount_ms = 0

    def __init__(self, character, part, item, action, frames=1):
        self.requires = set()
        self.character = character
        self.part = part
        self.item = item
        self.action = action
        self.tracker = None
        self.action_frames = frames
        self.start = RpgTick.CURRENT


class PsycheLeverage:
    """
    Model the application and psychological demands on a character for tracking
    of modifiers for interactions, this model explicitly identifies items in
    world and goal analysis between two or more characters.
    """
    name = ''
    description = ''
    related = None
    when = None
    total = 0
    aware = 0
    pivots = None

    @property
    def enforced(self):
        """
        Times this leverage has been enfoced upon a character.

        :return: int
        """
        return len(self.pivots)

    def aware_from(self, target):
        """
        Explicit awareness of a piece of leverage from a selected target.

        TODO: Not type validation on `target` due to cyclic imports 😢

        :param target: PlayerCharacter expected to be aware of this leverage.
        :return: float
        """
        return sum([p.total for p in self.pivots if p.target_from is target])

    def __init__(self, name, related):
        self.name = name
        self.related = related
        self.when = RpgTick.CURRENT
        self.pivots = []
        self.acknowledged = {}


class PsychePivot:
    """Psychological pivots to apply to a character."""
    TYPES = {
        'accepted': StatType(name='Accepted', ratio=1.5),
        'trusted': StatType(name='Trusted', ratio=1),
        'shunned': StatType(name='Shunned', ratio=-1),
        'rejected': StatType(name='Rejected', ratio=2),
        'betrayed': StatType(name='Betrayed', ratio=-10),
        'explored': StatType(name='Explored', ratio=-5),
        'analysed': StatType(name='Analysed', ratio=1),
        'phobia': StatType(name='Phobia', ratio=5),
    }

    name = ''
    description = ''
    target_from = None
    target_to = None
    when = None
    type = None
    related = None
    mapping = None
    total = 0
    rating = 0
    quantity = 0
    duration = 0
    multiplier = 1

    def __init__(self, **kwargs):
        for k in kwargs.keys():
            setattr(self, k, kwargs[k])
        if not self.type or type(self.type) is not StatType:
            raise Exception('Expected type for a pivot is a StatType.')
        else:
            self.type = duplicate_object(self.type)

    def __str__(self):
        return '<PsychePivot "{}": {}ms>'.format(
            self.type.name,
            self.duration * self.multiplier * self.type.ratio
        )


class StatGroup:
    """Defining group of stats, defaults: Stat, discipline, skill."""
    _name = ''
    search = ''
    description = ''
    base_value = 0
    stats = None
    alloc = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value or ''
        if not value:
            return
        self.search = value.replace(' ', '').lower()

    @property
    def allocated(self):
        """Points allocated to this StatGroup by player."""
        self.update()
        return sum([s.modified for s in self.stats])

    @property
    def education(self):
        """Points allocated to this StatGroup through education."""
        self.update()
        return sum([s.educated for s in self.stats])

    @property
    def assigned(self):
        """Points allocated to this StatGroup."""
        self.update()
        return sum([s.total for s in self.stats])

    @property
    def remaining(self):
        """Remaining points available for allocation."""
        return int(sum([a.ratio for a in self.alloc]) - self.allocated)

    def find(self, related, auto_create=True):
        """
        Find the statistic of a relational name:
        Passing in another statistic a found statistic from this known list
        will be returned with no match to object equality other than name id.
        For a none found statistic object in this list but a statistic is passed
        as a relational object a new statistic will be aded to the group as a
        separately managed object.
        Equality of string identifiers will be returned as normal.

        :param related: Stat | StatType | str
        :param auto_create: bool, to automatically create a statistic.
        :return: Stat or None
        """
        found = None
        names = [stat.search for stat in self.stats]
        if hasattr(related, 'name'):
            value_name = related.name.replace(' ', '').lower()
            if value_name in names:
                found = self.stats[names.index(value_name)]
        elif hasattr(related, 'type'):
            value_type = related.type.name.replace(' ', '').lower()
            if value_type in names:
                found = self.stats[names.index(value_type)]
        else:
            value = related.replace(' ', '').lower()
            names = [stat.search for stat in self.stats]
            if value in names:
                found = self.stats[names.index(value)]
        if not found and auto_create:
            found = Stat(name=related, group=self)
            if hasattr(related, 'type'):
                found.type = related.type
            if hasattr(related, 'group'):
                found.unknown['group'] = related.group
            Middleware.handle('Auto Stat Create', found, related)
            self.stats.append(found)
        return found

    def find_of_type(self, name):
        """
        Find the statistics which are bound by a type.

        :param name: str identifier for type name.
        :return: list
        """
        return [a for a in self.stats if a.type.name == name]

    def allocate(self, name, points=1):
        """
        Allocate a point to the specified statistic.

        :param name: Statistic name identifier to add points to.
        :param points: integer value modifying the statistic.
        """
        if self.remaining < points:
            print('Not enough allocation points, remaining: {}.'.format(
                self.remaining))
            return
        stat = self.find(name, auto_create=False)
        if not stat:
            print('Stat "{}" is not of this group "{}"'.format(name, self.name))
            return
        stat.modifiers.append(StatType(name='Modifier', ratio=points))
        stat.update()

    def consolidate(self, ceiling=1):
        """
        Condense all values into a single object.

        :param ceiling: float for the highest value to consolidate from.
        """
        value = sum([a.ratio for a in self.alloc if a.ratio < ceiling])
        if value == 0:
            return
        consolidated = StatType(name=self.name, ratio=value)
        new_alloc = [a for a in self.alloc if a.ratio >= ceiling]
        self.alloc = new_alloc + [consolidated]

    def update(self):
        """Update statistics associated with this group."""
        for s in self.stats:
            s.update()

    def __init__(self, name=None, description='', stats=None, base_value=0):
        self.name = name
        self.description = description
        self.stats = stats or []
        self.base_value = base_value
        self.alloc = []

    def __str__(self):
        l = ['{}: {}'.format(s.name, s.total) for s in self.stats]
        return '<StatGroup "{}", stats={}>'.format(
            self.name,
            str(l[:20]) if len(l) < 20 else str(l[:20])[:-1] + ', ...]'
        )


class Stat:
    """Basic stat option."""
    type = None
    _name = ''
    search = ''
    description = ''
    group = None
    time = -1
    interchange_time = 0
    difficulty = 0
    total = 0
    ratio = 0
    modified = 0
    educated = 0
    crossed = 0
    modifiers = None
    education = None
    pivots = None
    cross = None
    affect = None
    spread = None
    draw = None
    psyche = None
    unknown = None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value or ''
        if not value:
            return
        self.search = value.replace(' ', '').lower()

    def update_allocated(self):
        """Update modifiers of this statistic."""
        self.educated = sum([e.ratio for e in self.education])
        self.modified = sum([e.ratio for e in self.modifiers])

    def update(self):
        """
        Update all value related to this statistic.
        If this statistic identifies 'cross' stats then these will be updated
        before the tally which can incur additional computations.
        """
        if self.group is None:
            return
        total = self.group.base_value
        self.update_allocated()
        if self.cross:
            for item in self.cross:
                crossed = self.group.find(item.name)
                if not crossed:
                    continue
                crossed.update_allocated()
                alloc = crossed.modified + crossed.educated
                total += alloc * item.ratio
        self.total = total + self.modified + self.educated

    def __init__(self, name=None, group=None, cross=None, stat_type=None):
        self.name = name
        self.group = group
        self.cross = cross
        self.type = stat_type
        if self.group and self._name not in [g.name for g in self.group.stats]:
            self.group.stats.append(self)
        self.modifiers = []
        self.education = []
        self.psyche = []
        self.pivots = []
        self.affect = []
        self.spread = []
        self.draw = []
        self.unknown = {}
        self.time = 0

    def __str__(self):
        return '<Stat name: "{}", total: {}, group: "{}">'.format(
            self.name, self.total, self.group.name if self.group else 'None')


class LifeStage:
    """Defining range of time in someones life."""
    name = ''
    description = ''
    age_from = 0
    age_to = 0
    education = None
    expected = None
    location = None
    expenses = 0
    projected = 0
    decision = ''
    character = None

    def __init__(
            self, name='', description='', age_from=0, age_to=0, expected=[]
    ):
        self.name = name
        self.description = description
        self.age_from = age_from
        self.age_to = age_to
        self.expected = expected
        self.education = []

    def __str__(self):
        return '<LifeStage {}: {}-{}yrs>'.format(
            self.name,
            self.age_from,
            self.age_to,
        )


class LifeLocation:
    """Location within the universe"""
    name = ''
    long_name = ''
    description = ''
    geo = ''
    economy = ''
    postcode = ''
    number = ''
    building = ''
    street = ''
    district = ''
    planet = ''
    solar_system = ''
    galaxy = ''
    universe = ''
    income_percentiles = None
    age_distribution = None
    death_distribution = None
    wealth = 0
    movement = 0
    crime = 0
    religion = None

    def address(self):
        """
        Supply this location as an address.

        :return: list
        """
        return [
            self.number,
            self.building,
            self.street,
            self.district,
            self.planet,
            self.solar_system,
            self.galaxy,
            self.universe,
        ]

    def __init__(self, name=''):
        self.name = name
        self.income_percentiles = []
        self.age_distribution = []
        self.death_distribution = []


class ItemContainer:
    """Model an objects container."""
    weight = 0
    volume = 0
    weight_total = 0
    volume_total = 0
    quantity = 0
    items = None
    restrict = None
    quantity_max = -1
    max_weight = -1
    max_volume = -1
    parent = None
    q_max_type = {}

    def quantity_remaining(self):
        """The quantity allowed to be added to this container."""
        if not self.quantity_max:
            return True
        if int(self.quantity_max) <= 0:
            return 0
        self.quantity = sum([int(i.quantity) if i else 0 for i in self.items])
        return int(self.quantity_max) - self.quantity

    def measure(self):
        """Update the stats for this container."""
        self.weight_total = float(self.weight)
        self.volume_total = float(self.volume)
        self.quantity_remaining()
        for item in self.items:
            item.measure()
            self.weight_total += float(item.weight_total)
            self.volume_total += float(item.volume_total)

    def can_contain(self, item):
        """
        Provides a validation for item types, quantity, weight, and volume
        of this containers limits to hold items.
        """
        if not item:
            return False, 'No item to contain.'
        if (
            (not self.max_volume or self.max_volume < 0) and
            (not self.max_weight or self.max_weight < 0) and
            (not self.quantity_max or self.quantity_max < 0)
        ):
            return False, 'Is not a container.'
        if (
            self.quantity_max != -1 and
            self.quantity + 1 > self.quantity_max
        ):
            return False, 'Quantity exceeded for container.'
        if (
            self.max_volume != -1 and
            float(self.volume) + float(item.volume) > self.max_volume
        ):
            return False, 'Size of container cannot be exceeded.'
        if (
            self.max_weight != -1 and
            float(self.weight) + float(item.weight) > self.max_weight
        ):
            return False, 'Container will break if more is added.'
        item_descriptors = [
            item.name,
            item.type.name if item.type else None,
            item.group.name if item.group else None
        ] + [f.name for f in self.parent.functions]
        restricted_to = [
            r for r in self.restrict
            if r in item_descriptors
        ]
        if len(self.restrict) > 0 and not restricted_to:
            return False, str(
                'Type of object is not allowed to be stored here. '
                'Restrictions: {}'.format(self.restrict)
            )
        for r in restricted_to:
            if r in self.q_max_type.keys():
                q = self.search(item.name)
                q = q[0].quantity if q else 0
                if q + item.quantity > self.q_max_type[r]:
                    return False, str(
                        'Object type is restricted to a max quantity: "{}",'
                        'Allocation would exceed to: "{}"'
                    ).format(self.q_max_type[r], q + item.quantity)
        return True, None

    def add(self, item):
        """Preferred method to manage the adding to a container."""
        can_add, add_error = self.can_contain(item)
        if not can_add:
            raise Exception(add_error)
        if type(item) is str:
            raise Exception('Cannot add strings as objects.')
        found = self.search(item.name)
        if not found:
            self.items.append(item)
            found = item
        else:
            found = found[0]
            if not found.quantity:
                found.quantity = 1
            if type(found.quantity) is not int:
                found.quantity = int(found.quantity)
            found.quantity += int(item.quantity) or 1
        self.measure()
        Middleware.handle('ItemContainer Add', item, self)
        return found

    def remove(self, item=None, quantity=1):
        """Remove the indicated item from the container."""
        rtn = None
        if not item and self.items:
            item = self.items[0].name
        found = self.search(item if type(item) is str else item.name)
        if found:
            found_item = found[0]  # list returned for quantity based items
            if int(found_item.quantity) > quantity:
                found_item.quantity = int(found_item.quantity) - quantity
                rtn = duplicate_object(found_item)
                rtn.quantity = quantity
            else:
                rtn = found_item
                index = self.items.index(found_item)
                self.items = self.items[:index] + self.items[index + 1:]
            self.measure()
        Middleware.handle('ItemContainer Remove', rtn, self)
        return rtn

    def remove_first(self):
        """Remove the first item in the container."""
        rtn = self.remove(self.items[0]) if len(self.items) > 0 else None
        self.measure()
        return rtn

    def search(self, name, attribute='name'):
        """Simple exact match to the name of the items being contained."""
        rtn = []
        for item in self.items:
            test = getattr(item, attribute)
            flag = False
            if type(test) is str and test == name:
                flag = True
            elif type(test) in [list, tuple, set] and name in test:
                flag = True
            elif type(test) in [dict] and name in test.keys():
                flag = True
            if flag:
                rtn.append(item)
        return rtn

    def to_string(self):
        return '= quantity: {}, item{}: {}'.format(
            len(self.items),
            's' if len(self.items) > 1 else '',
            [str(n) for n in self.items],
        )

    def __init__(self, max_volume=-1, max_weight=-1, parent=None):
        self.max_weight = max_weight
        self.max_volume = max_volume
        self.items = []
        self.restrict = []
        self.parent = parent

    def __str__(self):
        trunc = len(self.items) > 5
        items = str([str(n) for n in self.items[:5]])
        return '<ItemContainer {} item{}: {}, restrictions: {}>'.format(
            len(self.items),
            's' if len(self.items) > 1 else '',
            items if not trunc else '{}{}'.format(items[:-1], ', ...]'),
            str(self.restrict),
        )


class EducationStat:
    """Block of education required to build a characters history."""
    type = None
    name = ''
    location = None  # LifeLocation
    abode = ''
    income = 0
    duration_years = 0
    position = None
    ratings = None
    relationships = None
    teachings = None
    cross_mappings = None

    def __init__(self, name=''):
        self.name = name
        self.ratings = []
        self.relationships = []
        self.teachings = []

    def __str__(self):
        return '<EducationStat {}, {}yrs, {}>'.format(
            self.name, self.duration_years, self.teachings)


class BodyPart:
    """Part of a larger bodied system to model a function object."""
    id = None
    type = None
    group = None
    name = ''
    description = ''
    vector = None
    manufacturer = None
    requires = None
    health_max = None
    armour = 0
    security = 0
    circulation = 0
    health = 0
    quantity = 1
    health_ms = 0
    main = False
    actions = None
    action_time = 0
    action_primary = None
    functions = None
    affect = None
    spread = None
    parent = None
    connections = None
    weight = 0
    volume = 0
    weight_total = 0
    volume_total = 0
    fatigue = 0
    guarantee = 0
    superstition = 0
    rrp = 0
    price = None
    time_interaction = 0
    contain_quantity = -1
    contain_volume = -1
    contain_weight = -1
    contain_restrictions = None
    contains = None
    wear_quantity = -1
    wear_volume = -1
    wear_weight = -1
    wear_restrictions = None
    wears = None
    imbued = None
    unknown = None
    for_sale = None
    for_junk = None
    body_state_id = None

    def _find(self, search, through='name', in_children=False):
        val = getattr(self, through)
        rtn = []
        if type(val) in [StatType, StatGroup]:
            val = val.name
        if type(val) in [list, tuple, set]:
            for v in val:
                if type(v) in [StatType, StatGroup]:
                    v = v.name
                if (
                    (type(search) in [list, tuple, set] and v in search) or
                    v == search
                ):
                    val = v
                    break
        if (
            (type(search) in [list, tuple, set] and val in search) or
            val == search
        ):
            rtn.append(self)
        if not in_children:
            return rtn
        for child in self.connections:
            if (
                not child or
                child in [self, self.parent] or
                type(child) is str or
                (type(child) is BodyPart and child.group.name in ['Medium'])
            ):
                continue
            rtn += child._find(
                search,
                through=through,
                in_children=True,
            )
        return rtn

    def _list_holds(self, hold, in_children=False):
        """
        List available holds from the parent.

        :param hold: str, type of hold being checked for 'container' or 'wear'.
        :param in_children: bool, default False, search connected BodyPart's.
        :return: list, containers avilable from this body part.
        """
        container = getattr(self, hold)
        containers = [self] if container else []
        method_name = 'list_{}'.format(hold)
        if not in_children:
            return containers
        for child in self.connections:
            if (
                not child or
                child in [self, self.parent] or
                type(child) is not BodyPart
            ):
                continue
            containers += getattr(child, method_name)(in_children=in_children)
        return containers

    def _holds_validate(self, item, hold):
        """
        Find and validate all holds able to contain the item.

        :param item: BodyPart, to check being able to be held in the container.
        :param hold: str, type of hold being checked for 'container' or 'wear'.
        :return: list, containers avilable and valid from this body part.
        """
        holds = self._list_holds(hold, in_children=True)
        containers = []
        for holder in holds:
            can_hold, reason = getattr(holder, hold).can_contain(item)
            if can_hold:
                containers.append(holder)
        return containers

    def _from_here(self, all_parts=False):
        """
        Find the location to start a search or recursive check.

        :param all_parts: Find root.
        """
        from_here = self
        if all_parts and self.parent:
            from_here = self.find_root()
        return from_here

    def find_root(self):
        """Find the root part of this body."""
        return self.parent.find_root() if self.parent else self

    def find_functions(self, *args, all_parts=False, in_children=True):
        """Find a body part by function."""
        return self._from_here(all_parts=all_parts)._find(
            args, 'functions', in_children=in_children)

    def find_action(self, *args, all_parts=False, in_children=True):
        """Find a body part by action."""
        return self._from_here(all_parts=all_parts)._find(
            args[0], 'actions', in_children=in_children)

    def find_group(self, *args, all_parts=False, in_children=True):
        """Find a body part by group."""
        return self._from_here(all_parts=all_parts)._find(
            args[0], 'group', in_children=in_children)

    def find_type(self, *args, all_parts=False, in_children=True):
        """Find a body part by type."""
        return self._from_here(all_parts=all_parts)._find(
            args[0], 'type', in_children=in_children)

    def find_name(self, *args, all_parts=False, in_children=True):
        """Find a body part by name."""
        return self._from_here(all_parts=all_parts)._find(
            args[0], in_children=in_children)

    def find_imbued(self, *args, all_parts=True, include_wears=True):
        """
        Active imbued affects applied to this and child BodyPart objects, the
        search takes efect not just for the name of the affect applied to the
        various BodyPart objects but the functions of the affect's.

        If no arguments are supplied or None then the parts imbued will be
        returned instead of the imbuings applied to an item. This goes against
        modern programming standards and should be reworked to provide the
        specific functionality per method instead of changing the functionality
        of this function.
        TODO: Refactor this method to not switch functionality.

        :param args: tuple of arguments were the first index is taken as search.
        :param all_parts: bool, indicating all BodyParts from this.
        :param include_wears: bool, items being worn by this BodyPart included.
        :return: list, all `Affect`s matching search.
        """
        parts = self.flatten_from(parent=self)
        search = args[0] if len(args) > 0 else None
        found = []
        for part in parts:
            if type(part) is str:
                continue
            affects = [
                a for a in part.connections
                if a.type.name == 'Construct' and a.group.name == 'Affect'
            ]
            if not search and affects:
                found.append(part)
            for affect in affects:
                functions = [f for f in affect.affect if f.name == search]
                if affect.name == search or functions:
                    found.append(affect)
        if include_wears:
            holds = self.list_wears(all_parts=all_parts)
            items = [w for i in holds for w in i.wears.items]
            for item in items:
                # HACK: Dirty circumvention of cyclic dependency.
                if hasattr(item, 'item_model'):
                    item = item.item_model
                found += item.find_imbued(
                    search, all_parts=all_parts, include_wears=include_wears)
        return found

    def find_wears(self, item, all_parts=False):
        """Find available wearable locations on this body."""
        return self._from_here(all_parts=all_parts)._holds_validate(
            item, 'wears')

    def find_contains(self, item, all_parts=False):
        """Find available containers of this body."""
        return self._from_here(all_parts=all_parts)._holds_validate(
            item, 'contains')

    def find_affect(self, name, all_parts=False, in_children=True):
        """
        Search through all items connected to this BodyPart and find the parts
        with the associated affects matching the name and optional value
        provided, for no value being provided those items with the name will be
        returned while the reverse will fail.

        :param name: str, value to search for as an affect of BodyParts.
        :param all_parts: bool, indicating all BodyParts from this.
        :param in_children: bool, include child connections.
        :return: list with found BodyPart objects.
        """
        return self._from_here(all_parts=all_parts)._find(
            name, through='affect', in_children=in_children)

    def list_wears(self, all_parts=False, in_children=True):
        """List the wearable locations of this body."""
        return self._from_here(all_parts=all_parts)._list_holds(
            'wears', in_children=in_children)

    def list_contains(self, all_parts=False, in_children=True):
        """Find all containers on a body."""
        return self._from_here(all_parts=all_parts)._list_holds(
            'contains', in_children=in_children)

    def find_packable(self, item):
        """
        Find the avaiable containers to contain the item passed in any of the
        wearable items being worn from this BodyPart and its connections.

        :param item: BodyPart, the object being managed.
        :return: ItemContainer, the first valid container found.
        """
        wears = self.list_wears()
        for wear in wears:
            contains = wear.find_contains(item)
            if contains:
                return contains[0]

    def find_packed(self, name):
        """
        Find items of the same type packed into the clothing of this and all
        connected BodyPart objects.

        :param name: str, the name to search for on the BodPart.
        :return: dict, detailing the container and items matching search needs.
        """
        rtn = {}
        for wear in self.list_wears():
            for contain in wear.list_contains():
                search = contain.search(name)
                if search:
                    rtn.update({contain: search})
        return rtn

    def flatten_from(self, parent=None):
        """
        Provide a representation of this object as a flat list.

        :param parent: BodyPart to start the flat representation from.
        :return: list
        """
        if not parent:
            parent = self.find_root() if self.parent else self
        rtn = {self}
        rtn.update(set(parent.connections))
        for child in parent.connections:
            if (
                not child or
                child in [parent, parent.parent] or
                type(child) is not BodyPart
            ):
                continue
            rtn.update(self.flatten_from(child))
        return rtn

    def measure(self, include_containers=True):
        """
        Measure this object and its child objects, this includes the weight,
        volume, health, and health_max, this should not be the only applicable
        measurement of this BodyPart but satisfies the majority required.

        To have containers not included in the calculation change the argument
        `include_containers` to False, this will have a great impact on
        calculations for characters with large carry weights. Expected or
        example uuse would be to understand a base level of interaction as a
        control comparison to the weighted character.

        As this model doesn't take into consideration the three dimensional
        characteristics of a body the height is calculated externally,
        expectantly reliant on 3D models to be measured and converted into
        meters.

        :param include_containers: Include the containers within measurement.
        :return: (float, float) representing (weight, volume)
        """
        weight = 0
        volume = 0
        health = 0
        health_max = 0
        if include_containers and self.contains:
            self.contains.measure()
            weight += float(self.contains.weight)
            volume += float(self.contains.volume)
        if include_containers and self.wears:
            self.wears.measure()
            weight += float(self.wears.weight)
            volume += float(self.wears.volume)
        for item in self.connections:
            if (
                not item or
                type(item) is not BodyPart or
                item.parent is not self
            ):
                continue
            item.measure(include_containers=include_containers)
            weight += float(item.weight_total or item.weight)
            volume += float(item.volume_total or item.volume)
            health_max += float(item.health_max)
            health += float(item.health)
        self.weight_total = weight
        self.volume_total = volume
        if self.health_max is None:
            self.health_max = health_max
            self.health = health
        Middleware.handle('Body Dimensions', self)
        return (
            self.weight_total * int(self.quantity),
            self.volume_total * int(self.quantity)
        )

    def function_ratio(self, *args):
        """The availability to provide the required functionality."""
        avail = [
            n.ratio
            for n in self.functions
            if n.name != args[0]
        ]
        return sum(avail) / len(avail) if avail else 1

    def __init__(self, name='', save_id=None, parent=None, container=False):
        self.id = hash_generate() if not save_id else str(save_id)
        self.name = name
        self.parent = parent
        self.actions = []
        self.functions = []
        self.affect = []
        self.spread = []
        self.connections = []
        self.contain_restrictions = []
        self.imbued = []
        self.unknown = {}
        if container:
            self.contains = ItemContainer()

    def inspect(self, prefix='', show_all=False):
        rtn = '{}Object ({}): {}\n'.format(prefix, self.group.name, self.name)
        rtn += '{} = RRP: {}, Weight: {}, Volume: {}\n'.format(
            prefix, self.rrp, self.weight, self.volume)
        if self.contains:
            rtn += '{} = Contains ({}): {}\n'.format(
                prefix,
                sum([int(i.quantity) for i in self.contains.items]),
                [c for c in self.contains.items]
            )
        parts = self.flatten_from()
        if show_all and len(parts) > 1:
            rtn += '{} = Modifiable parts {}:\n'.format(prefix, len(parts) - 1)
            for part in parts:
                if part is not self:
                    rtn += '{} | {}, rrp {}, functions: {}\n'.format(
                        prefix,
                        part.name,
                        part.rrp,
                        [str(f) for f in part.functions])
                    if part.contains:
                        rtn += '{} | = Contains ({}): {}\n'.format(
                            prefix,
                            sum([int(i.quantity) for i in part.contains.items]),
                            [
                                c.name + str(
                                    ': {} off'.format(c.quantity) if int(
                                        c.quantity) > 1 else ''
                                ) for c in part.contains.items
                            ]
                        )
        return rtn

    def to_short_string(self):
        return '<BodyPart "{}">'.format(self.name)

    def __str__(self):
        return '<BodyPart "{}", quantity: {}, child count: {}>'.format(
            self.name,
            self.quantity,
            (
                len(self.connections)
                if type(self.connections) is list else 0
            ),
        )


class TradeSlip:
    """
    Modeling items and units of trade available to transfer between two
    PlayerCharacter objects, this model is expected to manage sorting and
    provide calculations from each ability provided from trade partners.
    """
    id = None
    loan = False
    interest_rate = None
    items = None
    selected = None
    valuations = None
    debit = None
    receipt = None

    def __init__(self, items, valuations, expected_physical=1):
        if type(items) is not list or type(valuations) is not list:
            raise Exception('list of trade items required.')
        if len(valuations) != len(items):
            raise Exception(
                'valuations length does not match the number of items.')
        self.id = hash_generate()
        skip = [
            'id', 'contains', 'wears', 'imbued', 'price', 'parent',
            'action_time', 'action_primary', 'unknown',
        ]
        self.items = [duplicate_object(i, skip=skip) for i in items]
        self.valuations = valuations
        self.selected = []
        self.debit = ItemContainer(max_volume=expected_physical)
        self.debit.restrict = ['Credit']
        self.receipt = ItemContainer(max_volume=expected_physical)


class CharacterLicense:
    """
    Legal identification of a PlayerCharacter and their access to lifestyles.
    """
    license_type = None
    owner = None
    dna = None
    id = None
    rectifications = None
    location_issued = None
    date_issued = None
    date_expiry = None
    licenses = None
    offences = None

    @staticmethod
    def generate_id(alphabet=None, pattern='####-####<########>##'):
        """
        Produce a string value of a random hash with a formatting provided as
        pattern, denoting an alphanumeric value use the character '#' hash all
        other values will be discarded as part of the required format.

        :param alphabet: str, a list of characters expected to be used to
                              generate the hash, providing a list of numbers
                              will result in a hash of numbers only.
        :param pattern: str, the pattern required to produce the has in.
        :return: str
        """
        rtn = ''
        index = -1
        generated = hash_generate(length=len(pattern), alphabet=alphabet)
        pattern = pattern.split('#')
        for p in pattern:
            index += 1
            rtn += generated[index] if not p else p
        return rtn

    def __init__(self, owner, license_type, location=None):
        if not owner:
            raise Exception('Licenses require an owner at all times.')
        self.owner = owner
        if not license_type:
            raise Exception('Licenses are always a type, non supplied.')
        if license_type not in rpg_const.LICENSES.stats:
            if type(license_type) is str:
                license_type = [
                    l for l in rpg_const.LICENSES.stats
                    if l.name == license_type
                ]
                if not license_type:
                    raise Exception('No license found: "{}".'.format(
                         license_type))
                license_type = license_type[0]
            else:
                rpg_const.LICENSES.append(license_type)
        self.license_type = license_type
        self.id = CharacterLicense.generate_id()
        self.date_issued = RpgConst.YEAR_START_MINIMUM
        duration = int(license_type.expiry)
        self.date_expiry = RpgConst.YEAR_START_MINIMUM + duration
        self.location_issued = location if location else self.owner.location
        self.rectifications = []
        self.licenses = []
        self.offences = []


class CharacterAccount:
    """Account for the character relative to location."""
    owner = None
    name = ''
    description = ''
    location = None
    interest = 0
    tax_rate = 0
    default_dividend_rate = 0
    debit = None
    credit = None
    monthly_credit_repayment = 0
    annual_dividend = 0
    investments = None
    total_subscription = 0
    expected_month_end = 0
    subscriptions = None
    loans = None
    insurance = None
    trades = None

    def __init__(self, owner, name='Current Account'):
        self.owner = owner
        self.name = '{}\'s Current Account'.format(name)
        self.debit = ItemContainer(max_volume=1)
        self.debit.restrict = ['Credit']
        self.credit = ItemContainer(max_volume=1)
        self.credit.quantity_max = 0
        self.credit.restrict = ['Credit']
        self.investments = []
        self.subscriptions = []
        self.loans = []
        self.insurance = []
        self.trades = {}


class CharacterBody:
    """The body of a Character."""
    id = None
    name = ''
    soul = None
    species = None  # RpgSpecies
    gender = None  # RpgSpeciesGender
    birth_when = 0
    death_when = 0
    life_stages = None
    job = None  # EducationStat
    stats = None  # StatGroup
    brain = None  # BodyPart
    whole = None  # BodyPart
    contains = None
    social = None
    activities = None
    accounts = None
    licenses = None
    location = None  # LifeLocation
    first_hand = 'Right Hand'

    _weight_assigned = None

    @property
    def age(self):
        """
        The age of this body.

        :return: float
        """
        eldest_known = 0
        for stage in self.life_stages:
            if stage.age_to > eldest_known:
                eldest_known = stage.age_to
        return eldest_known

    @property
    def weight(self):
        """
        The weight of this body.

        :return: float
        """
        if self._weight_assigned:
            return self._weight_assigned
        if not self.whole:
            return -1
        self.whole.measure()
        return self.whole.weight

    @weight.setter
    def weight(self, value):
        self._weight_assigned = value

    @property
    def height(self):
        """
        The height of this body.

        :return: float
        """
        if not self.whole:
            return -1
        self.whole.measure()
        return self.whole.unknown['height']

    def find_functions(self, search):
        """Find a body part by function."""
        return self.whole.find_functions(search)

    def find_action(self, search):
        """Find a body part by action."""
        return self.whole.find_action(search)

    def find_type(self, search, all_parts=False, in_children=False):
        """Find a body part by type."""
        return self.whole.find_type(
            search, all_parts=all_parts, in_children=in_children)

    def find_name(self, search):
        """Find a body part by name."""
        return self.whole.find_name(search)

    def find_wears(self, item):
        """Find available wearable locations on this body."""
        return self.whole.find_wears(item) if self.whole else []

    def find_contains(self, item):
        """
        Find available containers of this body.

        :return: list
        """
        containers = []
        if self.whole:
            containers = self.whole.find_contains(item)
        elif self.contains and self.contains.can_contain(item):
            containers = self.contains
        return containers

    def list_wears(self):
        """List the wearable locations of this body."""
        return self.whole.list_wears() if self.whole else None

    def list_contains(self):
        """Find all containers on a body."""
        return self.whole.list_contains() if self.whole else self.contains

    def first_account(self):
        """
        Find the local CharacterAccount being used for this location.

        :return: CharacterAccount
        """
        if not len(self.accounts):
            return None
        rtn = [
            a for a in self.accounts
            if not a.location or a.location.economy == self.location.economy
        ]
        return rtn[0]

    def __init__(self, soul, name='', save_id=None, global_container=False):
        """
        Modeling the body of a character.

        By default every human doesn't have a container wrapping their body,
        nor does any other creature in the universe, meaning the default
        access to a global container is wrong. To give developers the fullest
        ability to have AI and bodiless entities acting in the world an ability
        to possess items, this 'global' container for a body is argument toggled
        or externally managed.

        :param soul: CharacterSoul, the soul bound to this body.
        :param name: str, name of this character's body.
        :param global_container: bool, provision of a global item store.
        """
        self.id = save_id or hash_generate()
        self.soul = soul
        self.name = name
        if global_container:
            self.contains = ItemContainer()
        self.life_stages = []
        self.social = []

    def __str__(self):
        return '<CharacterBody name: "{}">'.format(self.name)


class Indicator(RpgTick):
    """An indicator of a character"""
    DEFAULT = [
        'Health', 'Energy', 'Concentration', 'Fatigue', 'Carry Weight',
        'Peak Carry Weight',
    ]
    REV_RATIO = ['Carry Weight', 'Peak Carry Weight', ]

    type = None
    min = -1
    offset = -1
    max = -1
    ratio = None
    ms = None
    last = None
    character = None

    @property
    def value(self):
        """Get the total value for this Indicator."""
        return self.max - self.offset

    def _ratio_update(self):
        self.ratio = self.value / self.max if self.value > 0 else 0
        if self.type.name in Indicator.REV_RATIO:
            self.ratio = 1 - self.ratio

    def set(self, value):
        """
        Define the value at which this indicator is currently.

        TODO: Update for weight of character required as self.pool description.

        :param value: int, value to set this indicator to.
        """
        if value > self.max:
            value = self.max
        if value < self.min:
            value = self.min
        self.offset = self.max - value
        self._ratio_update()

    def pool(self, value):
        """
        Apply more of a value to this indicator into its `pool`.

        TODO: For Carry Weight being used as an indicator change the weight as
              a whole character, making the whole body become fatter or thinner
              as a whole while calculating the max capacity and offsetting the
              carried items' weight.

        :param value: int, value to pool into this indicator.
        :return int, the value allocated to the pool.
        """
        if value + self.value < 0:
            value = self.value
        if value + self.offset < 0:
            value = self.offset
        self.offset = self.offset + value
        self._ratio_update()
        return value

    def draw(self, value):
        """
        Draw a lump sum from the pool of this Indicator.

        TODO: Update for weight of character required as self.pool description.

        :param value: int, value to draw from this indicator.
        :return int, the value removed.
        """
        outcome = self.value - value
        if outcome < self.min:
            value = self.value
        self.offset += value
        self._ratio_update()
        return value

    def tick(self):
        """
        Update this Indicator to represent the characters vital statistics.
        """
        self.draw(RpgTick.DIFF * self.ms)

    def calc_max(self):
        """Maximum calculations expected for different types of Indicator."""
        if not self.character.body:
            return
        if self.type.name == 'Health':
            if not self.character.body or not self.character.body.whole:
                self.max = 0
            else:
                vitals = self.character.body.whole.find_type(
                    'Vital', all_parts=True)
                self.max = sum([int(part.health_max) for part in vitals])
        elif self.type.name == 'Carry Weight':
            # TODO: Values of character body are available just not represented.
            self.max = (
                self.character.body.species.carry_by_weight *
                self.character.body.weight
            )
        elif self.type.name == 'Peak Carry Weight':
            # TODO: Values of character body are available just not represented.
            strength_ratio = (
                self.character.stats.find('Strength').total *
                self.character.body.species.carry_by_strength
            )
            if strength_ratio < 1:
                strength_ratio = 1
            self.max = (
                self.character.body.species.carry_by_weight *
                self.character.body.weight
            ) * strength_ratio
        elif self.type.name == 'Energy':
            self.max = (
                self.character.body.species.energy_base *
                self.character.stats.find('Willpower').total *
                self.character.stats.find('Psychic').total *
                self.character.stats.find('Metabolism').total
            )
            stress = float(self.character.disorders.find('Acute Stress').total)
            if stress > 0:
                self.max /= stress
            elif stress < 0:
                self.max *= -1 * stress
        elif self.type.name == 'Concentration':
            self.max = (
                self.character.body.species.concentration_base *
                self.character.stats.find('Willpower').total *
                self.character.stats.find('Belief').total *
                self.character.stats.find('Intelligence').total
            )
            psychotic = float(
                self.character.disorders.find('Psychotic Disorder').total)
            if psychotic > 0:
                self.max /= psychotic
            elif psychotic < 0:
                self.max *= -1 * psychotic
        elif self.type.name == 'Fatigue':
            self.max = (
                self.character.body.species.fatigue_base *
                self.character.stats.find('Strength').total *
                self.character.stats.find('Metabolism').total *
                self.character.stats.find('Endurance').total
            )
            depression = float(
                self.character.disorders.find('Depression').total)
            if depression > 0:
                self.max /= depression
            elif depression < 0:
                self.max *= -1 * depression
        # TODO: Cybernetic and Nanotech additions expected relevant function

    def __init__(
            self, indicator_type, character, max=100, min=0, *args, **kwargs
    ):
        if type(indicator_type) is not StatType:
            indicator_type = StatType(name=indicator_type)
        self.type = indicator_type
        self.character = character
        self.max = max
        self.min = min
        self.ms = 0
        self.offset = 0
        super().__init__(*args, **kwargs)


class BodyVector:
    """Model dedicated to 3D space representation of physics."""
    position = None
    speed = None
    looking = None
    targeting = None
    direction = None
    posture = None
    # `tangent` is the lateral movement of the parent body's BodyVector
    tangent = None

    def __init__(
        self,
        position=None, speed=None, looking=0, direction=0, posture=None,
        tangent=None,
    ):
        self.position = position
        # HACK: Hard coded information on a model
        self.speed = speed or ('Still', 0)
        self.direction = direction
        self.posture = posture
        self.tangent = tangent

    def __str__(self):
        return '<BodyVector x,y,z: {}, speed: {}, direction: {}>'.format(
            self.position, self.speed, self.direction)


class CharacterSoul:
    """
    CharacterSoul defines a character to play in game, also known as a soul.

    NPC characters are expected to be exactly the same as a normal player's
    character model even allocating a minor version of an AI as a slave input
    for this characters actions. Human interaction would then override the
    systems AI controlling this character; functionally within the world this
    allows for the automation of people and machines as characters to be
    possessed by the player through a psychic ability.
    """
    id = None
    ai = None
    indicators = None
    carry_weight = 0
    peak_carry_weight = 0
    conscious = 0
    body = None
    name = ''
    bound_bodies = None
    available = True
    stats = None
    stats_soul = None
    disciplines = None
    skills = None
    abilities = None
    disorders = None
    phobias = None
    public = None
    divined_souls = None
    leveraged = None

    def find_stat(self, name, group=None):
        """
        Provide a list of stats from the name given.

        :param name: Name of stat required
        :param group: Type of stat specifically to search in
        :return: list
        """
        stats = (
            self.stats.stats +
            self.disciplines.stats +
            self.skills.stats
        )
        rtn = [
            n for n in stats
            if n.name == name and (not group or n.group.name == group)]
        if not rtn:
            return None
        return rtn if len(rtn) > 1 else rtn[0]

    def indicator(self, name):
        """Get the indicator of name."""
        return [i for i in self.indicators if i.type.name == name]

    def _create_default_indicators(self):
        self.indicators = []
        for ind in Indicator.DEFAULT:
            self.indicators.append(Indicator(ind, self))

    def __init__(self, name='nobody'):
        self.id = hash_generate()
        self.name = name
        self.disciplines = StatGroup(name='Disciplines')
        self.skills = StatGroup(name='Skills')
        self.abilities = StatGroup(name='Abilities')
        self.bound_bodies = []
        self.bound_bodies.append(CharacterBody(soul=self, name=name))
        self.public = []
        self.divined_souls = []
        self.leveraged = []
        self._create_default_indicators()

    def __str__(self):
        return '<CharacterSoul name: "{}">'.format(
            self.body.name if self.body else self.name,
        )
