"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence
Email: vesper.porta@protonmail.com

Defining methods available to the character object for a playable character.

To create a character as a soul:
```
soul = PlayerCharacter(nobody=True)
```

To create a character from loaded data the expected is being penned although an
exception will be raised if attempted as this feature is due post MVP, a similar
object recovery mechanic is available for ObjectItem's:
```
char = PlayerCharacter(save_id='char_id')
item = ObjectItem(save_id='item_id')
```

# TODO: Post MVP. Load data for character and object item recovery.

The save_id or ObjectItem objects is not the same as 'search' for one reason:
saved items are modified originals where the search value is for an original.
This can clearly be consolidated into one field and is expected to be depending
on performance hit from searching through two database tables instead of one.

This file is expected to be split up with the ObjectHandler and Binding
management classes being provided from another module `management.py`, which
would serve pure functionality on top of the current classes.
"""

import importlib

from math import sqrt, ceil
from random import random, choice

from factories import (
    build_object_item, create_character_stats, create_character_body,
    convert_life_to_social, convert_life_to_activities,
    create_life_stage_eduction,
)
from load_data import search_effect_many, search_effect
from models import (
    RpgTick, Interaction, rpg_const, BodyVector, PsychePivot,
    CharacterBody, CharacterSoul, StatGroup, Stat,
    BodyPart, Indicator, ItemContainer, StatType, TradeSlip, PsycheLeverage,
    CharacterAccount, CharacterLicense,
)
from rpg_util import (
    duplicate_object, hash_generate, Middleware, mass_to_energy, ease_mult,
    impact_velocity, impact_energy, ease_mult_cap
)
from builtin_data import (
    POSTURE_TYPES, MOVEMENT_MAP, MOVEMENT_TYPES
)


class Binding:
    """
    Basic management for bindings of interactions.
    """
    DEFAULT = []
    MULTI = []
    CONSCIOUS_INDEPENDENT = ['q', 'h', 'f', 'u', 'd']

    character = None
    bound = []
    skip_binding_down = []
    skip_binding_up = []
    npc_prefix = None

    @staticmethod
    def _multi_bound(character):
        """
        Get the bindings for the character passed.

        :param character: PlayerCharacter, the character to identify bindings of

        :return: Binding
        """
        if type(character) is not PlayerCharacter:
            return
        for player_binding in Binding.MULTI:
            if player_binding.character == character:
                return player_binding.bound
        return None

    def known_binding(self, binding, character=None):
        """
        Get the known bindings, optional for a particular character.

        :param binding: str, character to check for a binding.
        :param character: PlayerCharacter, targeted for the binding check.

        :return: str
        """
        bound = self.bound
        if character:
            bound = Binding._multi_bound(character)
        if self.npc_prefix:
            if binding.index(self.npc_prefix) < 0:
                return None
            binding = binding.replace(self.npc_prefix, '')
        binding = binding.lower()
        known = [b[1] for b in bound if b[0] == binding]
        return known[0] if len(known) else None

    def time_binding(self, binding, character=None):
        """
        Get the known binding with a time allocation to it.

        :param binding: str, character to check for a binding.
        :param character: PlayerCharacter, targeted for the binding check.

        :return: str
        """
        bound = self.bound
        if character:
            bound = Binding._multi_bound(character)
        known = [b[2] for b in bound if b[0] == binding.lower() and b[2]]
        if len(known) < 1:
            return None
        return int(known[0])

    def set_binding(self, binding, defined):
        """Set bindings for multi players"""
        try:
            known = self.known_binding(binding.lower())
        except Exception:
            print('Unknown binding being allocated.')
            return
        used = None
        for player_bindings in Binding.MULTI:
            try:
                used = player_bindings.known_binding(defined.lower())
            except Exception:
                pass
            if used:
                print('Binding already used.')
                return
        index = 0
        while index < len(self.bound):
            if self.bound[index][0] == known:
                self.bound[index][1] = defined.lower()
            index += 1

    def __init__(self, character):
        self.character = character
        if self.character.npc is True:
            self.npc_prefix = '{}_'.format(self.character.id)
        self.bound = [b[:] for b in Binding.DEFAULT]
        Binding.MULTI.append(self)


class CharacterHandler(object):
    """
    Management class for PlayerCharacter objects.
    """

    @staticmethod
    def evaluate_level(char, modifier=1):
        """
        Convert the PlayerCharacter to a level integer.
        This value is not a stepped assertion of a characters progress but
        the derived evaluation of the PlayerCharacter object.

        When using the modifier named argument with a value above 0 the value
        of level should be used to quickly understand the difference in
        levels between a PlayerCharacter and the modified number of allocation
        points expected to be assigned to an NPC character.

        :param char: PlayerCharacter object to evaluate
        :param modifier: int value required to 'level' up or down.
        :return: int
        """
        if modifier < 1:
            # TODO: Post MVP. Update helper to handle negative modifiers.
            raise Exception('You can not have a modifier below 1')
        masteries = int(
            sum([a.time for a in char.character.abilities.stats]) /
            rpg_const.MASTERY_MILLISECONDS
        )
        stat = (
            char.character.stats.base_value +
            char.character.stats.education +
            (rpg_const.EPIPHANY_RATIO['stats'] * masteries)
        )
        discipline = (
            char.character.disciplines.base_value +
            char.character.disciplines.education +
            (rpg_const.EPIPHANY_RATIO['disciplines'] * masteries)
        )
        skill = (
            char.character.skills.base_value +
            char.character.skills.education +
            (rpg_const.EPIPHANY_RATIO['skills'] * masteries)
        )
        skill_rate = char.character.stats.base_value / skill
        skill_exchange = skill_rate - (
            skill_rate * rpg_const.EXPERIENCE_EXCHANGE['skills_stats'])
        discipline_rate = char.character.stats.base_value / discipline
        discipline_exchange = discipline_rate - (
            discipline_rate *
            rpg_const.EXPERIENCE_EXCHANGE['disciplines_stats'])
        stat *= modifier
        discipline *= modifier
        skill *= modifier
        rtn = int(
            stat +
            (discipline * discipline_exchange) +
            (skill * skill_exchange)
        )
        return rtn

    @staticmethod
    def personalise(item, character):
        """
        Taking a characters stats and abilities to modify an items effectiveness
        away from 0 as possible, giving the outer limits capable of the item
        used by the selected character.

        :param item: ObjectItem or BodyPart to be personalised.
        :param character: PlayerCharacter personalising the item.
        :return: item passed with modifications of personalisation.
        """
        ObjectHandler.reset_affects(item)
        modify = item
        if issubclass(item.__class__, ObjectItem):
            modify = item.item_model
        if type(character) is PlayerCharacter:
            character = character.character
        affects = [duplicate_object(affect) for affect in modify.affect]
        for affect in affects:
            damage = [
                d for d in rpg_const.DAMAGE.stats if d.name == affect.name]
            modifiers = []
            for d in damage:
                if hasattr(d, 'functions'):
                    modifiers += d.functions
            for modifier in modifiers:
                ability = character.abilities.find(modifier)
                mod = StatType(name=ability.name)
                ability = AbilityHandler.as_ability(
                    ability, character=character)
                mod.ratio *= ability.accustomed
                affect.modifiers.append(mod)
        if modify.type.name == 'Construct':
            ability = character.abilities.find(modify, auto_create=False)
            if ability:
                ability = AbilityHandler.as_ability(
                    ability, character=character)
                if modify.contains.quantity_max > -1:
                    modify.contains.quantity_max *= ability.accustomed
                if modify.contains.max_weight > -1:
                    modify.contains.max_weight *= ability.accustomed
                if modify.contains.max_volume > -1:
                    modify.contains.max_volume *= ability.accustomed
        for connection in modify.connections:
            CharacterHandler.personalise(connection, character)
        return item

    @staticmethod
    def licenses_regional(character):
        """
        Select the licenses expected to be useful and owned by the
        PlayerCharacter passed.

        :param character: PlayerCharacter holding the licenses.
        :return: list, list of localises licenses.
        """
        if type(character) is PlayerCharacter:
            character = character.character
        if type(character) is CharacterSoul:
            character = character.body
        location = character.location
        if not location:
            return character.licenses
        location = location.address()
        found = []
        for license in character.licenses:
            if type(license.location) is str:
                if '|' in license.location:
                    license.location = license.location.split('|')
                else:
                    license.location = [license.location]
            count = len(license.location)
            for loc in location:
                if loc in license.location:
                    count -= 1
            if count == 0:
                found.append(license)
        return found

    @staticmethod
    def license_submission(character, license_name):
        """
        Supply the required information and leverage requirements as a means to
        have a license issued for specific activities and access to areas.
        Submission processes take different leverages on an official level with
        the option to have a PlayerCharacter house an finite amount of licenses
        to issue, this would give a governing body the ability to act as a
        psychology through outlets: AI, buildings, officials.

        Leverage provided by the character will be used automatically, any items
        on the character required for the license to be submitted will be
        removed from the character while the submission is being carried out. A
        unsuccessful submission will have items returned immediately.

        TODO: Add the optional PlayerCharacter interaction to vet submissions.

        :param character: PlayerCharacter requesting the license.
        :param license_name: str, name of the license being requested.
        :return: bool, success of submission.
        """
        pass

    @staticmethod
    def license_issued(character, license, returned_items=[]):
        """
        Assign a validated license to a PlayerCharacter checking for the
        relevant qualifications expected of any one license being issued while
        giving feedback in psychology reflecting the issuing.

        Items expected to be returned to the character will be added to the
        character through a 'Bid' incoming_incoming action for each item.

        :param character: PlayerCharacter being issued with the license.
        :param license: CharacterLicense, issued and being handed over.
        :param returned_items: list, items returned to the character.
        :return:
        """
        pass


class AbilityHandler(object):
    """
    Ability manager dealing with an ability from a PlayerCharacter.
    """
    # TODO: Weakref the references on constants to no require but prefer GC.
    PATHS = {}
    ABILITY_MEDIUMS = {}
    DISTANCE_IRRELEVANT = ['Manipulation', 'Movement', ]

    @staticmethod
    def ability_medium(ability):
        """
        Identify and return the applicable 'Medium' connection between two
        interacting objects.

        :param ability: Interaction, the ability being used as an Interaction.
        :return: MediumChannel, the medium found applicable for connection.
        """
        if ability.name in AbilityHandler.ABILITY_MEDIUMS.keys():
            return AbilityHandler.ABILITY_MEDIUMS[ability.name]
        results = search_effect_many('Medium', cache=True)
        for medium in results:
            a_skill = getattr(ability, 'skill', '')
            if type(a_skill) is not str:
                a_skill = a_skill.name
            a_discipline = getattr(ability, 'discipline', '')
            if type(a_discipline) is not str:
                a_discipline = a_discipline.name
            if (
                ability.name not in medium.functions and
                a_skill not in medium.functions and
                a_discipline not in medium.functions
            ):
                continue
            medium = MediumChannel(medium.name)
            AbilityHandler.ABILITY_MEDIUMS[ability.name] = medium
            # TODO: Dynamic abilities need skill and discipline added.
            return medium

    @staticmethod
    def connection_path(interaction):
        """
        Get the full path connecting an item to a character determined by the
        interaction happening.

        :param interaction: Interaction currently requiring a path.
        :return: list
        """
        if interaction in AbilityHandler.PATHS.keys():
            return AbilityHandler.PATHS[interaction]
        if not interaction.item and not interaction.character:
            return None
        item_path = interaction.item.item_model.find_functions(
            *interaction.action)
        char_path = interaction.character.character.find_functions(
            *interaction.action)
        path = char_path + item_path
        AbilityHandler.PATHS[interaction] = path
        return path

    @staticmethod
    def distance_ratio(interaction, kilometers=None):
        """
        Calculate the distance ratio expected of this interaction, the distance
        is taken from the interaction object itself if no distance is given
        explicitly.

        :param interaction: Interaction, current interaction being processed.
        :param kilometers: float, optional distance to calculate for.
        :return: float, the success ratio at the specified distance.
        """
        distance_km = kilometers if kilometers else interaction.distance_km
        modifier = 'Accuracy'
        affects = interaction.part.find_imbued(modifier)
        accustomed = interaction.accustomed + sum(
            [f.ratio for a in affects for f in a.affect if f.name == modifier])
        return 1 - ease_mult_cap(
            distance_km or 0,
            accustomed / rpg_const.DISTANCE_STEP
        )

    @staticmethod
    def distance_difficulty(ability, interaction):
        """
        Check if the target being interacted with is remote from the body
        and needs a medium to connect through, the distance the target is away
        from the character means the difficulty is increased for regular
        actions.

        :param ability: Stat determining the ability being used for interaction.
        :param interaction: Interaction checked for remote targeting.
        :return: float
        """
        medium = AbilityHandler.ability_medium(ability)
        if not medium:
            Middleware.handle('Distance No Medium', interaction)
            interaction.distance_ratio = 0
            return 0
        if '|' in medium.item_model.requires:
            requires = medium.item_model.requires.split('|')
        else:
            requires = [medium.item_model.requires]
        relevance = sum([
            1
            for r in requires
            if r in AbilityHandler.DISTANCE_IRRELEVANT
        ]) / len(requires)
        if not relevance:
            interaction.distance_ratio = 0
            return interaction.distance_ratio
        resistance = ease_mult(
            rpg_const.CIRCULATION_ZERO - float(medium.item_model.circulation),
            1)
        Middleware.handle('Distance KM', interaction)
        interaction.distance_ratio = AbilityHandler.distance_ratio(interaction)
        interaction.distance_ratio *= float(resistance)
        return interaction.distance_ratio

    @staticmethod
    def many_as_ability(abilities, interaction=None, character=None):
        """
        Take a list of abilities and return with a single ability definition
        combining all abilities expected. For those not able to be found no
        additional action will be taken and skipped.

        :param abilities: list, list of strings defining search options.
        :param interaction: Interaction, optional action being carried out.
        :param character: PlayerCharacter, optional character if no interaction.
        :return: Interaction, a representation common to defining as ability.
        """
        character = character
        if interaction and interaction.character:
            character = interaction.character
        if type(character) is not PlayerCharacter:
            return None
        rtn = Interaction(character)
        rtn.phobia_ratio = 0
        rtn.disorder_ratio = 0
        attributes = [
            'modifier', 'accustomed', 'phobia_ratio', 'disorder_ratio',
            'energy_draw', 'energy_ms', 'fatigue_draw', 'fatigue_ms',
            'concentration_draw', 'concentration_ms', 'amount_draw',
            'amount_ms',
        ]
        for ability in abilities:
            ability = character.character.abilities.find(ability)
            if not ability:
                continue
            capable = AbilityHandler.as_ability(ability, interaction)
            for a in attributes:
                setattr(rtn, a, getattr(rtn, a) + getattr(capable, a))
        for a in attributes:
            setattr(rtn, a, getattr(rtn, a) / len(abilities))
        return rtn

    @staticmethod
    def ability_definitions(ability, character):
        """
        Ensure a stat is updated with all required properties are provided from
        an ability Stat.

        :param ability: Stat defining the ability.
        :param character: The character to provide additional information from.
        :return: Interaction
        """
        if not ability:
            return ability
        skill = None
        discipline = None
        stat = None
        missing = []
        for attribute in ['skill', 'discipline', 'stat']:
            if (
                    not hasattr(ability, attribute) or
                    not getattr(ability, attribute)
            ):
                missing.append(attribute)
        if not missing:
            return ability
        if 'group' in ability.unknown.keys():
            group = ability.unknown['group']
            if ability.type.name == 'Construct':
                group = ability.type
            name = group.name
            skill = character.skills.find(name)
            discipline = skill.discipline
            if type(discipline) is not str:
                discipline = discipline.name
            discipline = character.disciplines.find(discipline)
            stat = skill.stat
            if type(stat) is not str:
                stat = stat.name
            stat = character.stats.find(stat)
        if skill and not hasattr(ability, 'skill'):
            setattr(ability, 'skill', skill)
        if discipline and not hasattr(ability, 'discipline'):
            setattr(ability, 'discipline', discipline)
        if stat and not hasattr(ability, 'stat'):
            setattr(ability, 'stat', stat)
        return ability

    @staticmethod
    def as_ability(ability, interaction=None, character=None):
        """
        Define this Stat as a set of values demanded from an ability action.

        :param ability: Ability statistic to provide interaction amounts.
        :param interaction: Interaction model.
        :return: Interaction
        """
        if not interaction:
            interaction = Interaction(None, None, None, None)
        ability.update()
        if type(ability.difficulty) is str:
            ability.difficulty = float(ability.difficulty)
        if interaction.character:
            character = interaction.character.character
        AbilityHandler.ability_definitions(ability, character)
        item_object = interaction.item
        joules = mass_to_energy(item_object.weight if item_object else 1)
        medium_skill = character.skills.find('Medium')
        discipline_skill = character.skills.find('Discipline')
        conditioning_skill = character.skills.find('Conditioning')
        energy = character.indicator('Energy')[0]
        fatigue = character.indicator('Fatigue')[0]
        concentration = character.indicator('Concentration')[0]
        self_total = interaction.timing or 1
        self_difficulty = (
            AbilityHandler.distance_difficulty(ability, interaction)
            if not interaction.distance_ratio else
            interaction.distance_ratio
        )
        self_difficulty += float(ability.difficulty) or 1
        # TODO: Ability cross requirements modification.
        # TODO: Apply psychology to the ability difficulty.
        skill = None
        if hasattr(ability, 'skill') and type(getattr(ability, 'skill')) is str:
            skill = character.skills.find(getattr(ability, 'skill'))
            if skill:
                setattr(ability, 'skill', skill)
        interaction.accustomed = ease_mult(
            int(ability.interchange_time or 100) + (
                discipline_skill.total * self_total),
            rpg_const.MASTERY_MILLISECONDS
        )
        interaction.energy_ms = (
            joules / (
                ((medium_skill.total * self_total) / self_difficulty) *
                interaction.accustomed * energy.max
            ) * rpg_const.ENERGY_RATIO
        )
        if skill:
            ratio = float(skill.unknown['Energy Draw Ratio'])
            if ratio:
                interaction.energy_draw = interaction.energy_ms * ratio
        interaction.fatigue_ms = (
            joules / (
                ((conditioning_skill.total * self_total) / self_difficulty) *
                interaction.accustomed * fatigue.max
            ) * rpg_const.ENERGY_RATIO
        ) if character.body else fatigue.max
        if skill:
            ratio = float(skill.unknown['Fatigue Draw Ratio'])
            if ratio:
                interaction.fatigue_draw = interaction.fatigue_ms * ratio
        interaction.concentration_ms = (
            joules / (
                discipline_skill.total * self_total * interaction.accustomed *
                concentration.max
            ) * rpg_const.ENERGY_RATIO
        )
        if skill:
            ratio = float(skill.unknown['Concentration Draw Ratio'])
            if ratio:
                interaction.concentration_draw = (
                    interaction.concentration_ms * ratio)
        interaction.amount_draw = (
            (interaction.accustomed * (self_total / self_difficulty))
        )
        return interaction


class PsycheHandler(RpgTick):
    """
    Management of a characters psychology and the interactions between two or
    more actors.
    """

    @staticmethod
    def deviancy_multiplier(character):
        """
        Determine a value measuring the likelihood of deviant behaviours from
        a character, this multiplier is expected to be used in conjunction with
        abusive checks and sentencing if caught by the authorities against the
        characters psychological profile.

        :param character: PlayerCharacter being vetted for deviancy
        :return: float, derived value indicating the deviancy of a psyche.
        """
        values = []
        offencive = []
        for key, value in enumerate(rpg_const.DAMAGE_CRIMINAL):
            disorder = character.disorders.find(value.name)
            if not disorder or disorder.total > 0:
                continue
            offencive.append(value)
            values.append(value.total)
            if value.functions:
                values.append(sum([
                    b.ratio * character.disorders.find(b.name).total
                    for b in value.functions
                ]))
            if value.resistance:
                # TODO: Confirm application of negative ratios
                values.append(sum([
                    r.ratio * character.disorders.find(r.name).total
                    for r in value.resistance
                ]))
        return ease_mult(values, len(offencive))

    @staticmethod
    def psychoses_multiplier(interaction, ability=None):
        """
        Provide a value from -1 through 1 to define a fear is active.

        :param interaction:
        :param ability:
        :return:
        """
        # TODO: Rewrite for validity in use and expectations
        character = interaction.character.character
        if not ability:
            ability = character.abilities.find(interaction.item)
        rtn = sum([psych.ratio for psych in ability.psyche])
        rtn = rtn / len(ability.psyche) if len(ability.psyche) > 0 else 0
        Middleware.handle('Psychoses Multiplier', interaction, ability, rtn)
        return rtn

    @staticmethod
    def build_psyche_map(character, ability):
        """
        Provide a Stat object with the defined psychologies erquired to manage
        the actions derived from any interaction requiring this ability.

        # TODO: Refactor for validity in use and expectations

        :param character: PlayerCharacter, sexpecting the map built for.
        :param ability: Stat, ability requiring the map built.
        """
        tmp_map = []
        stat_map = []
        psyche_map = []
        discipline = ''
        skill = ''
        stat = ''
        if 'Discipline' not in ability.unknown.keys():
            discipline = ability.unknown['group'].name
            skill = ability.type.name
            ability.unknown.update(
                {'Discipline': discipline, 'Skill': skill})
        if not discipline:
            discipline = ability.unknown['Discipline']
        discipline = character.find_stat(discipline)
        if not skill:
            skill = ability.unknown['Skill']
        skill = character.find_stat(skill)
        if not stat:
            stat = skill.unknown['Stat']
        type_name = discipline.type.name
        tmp_map += [skill.name, discipline.name]
        tmp_map += type_name.split('|') if '|' in type_name else [type_name]
        tmp_stat = stat
        if type(stat) is str:
            if '|' in stat:
                tmp_stat = stat.split('|')
            else:
                tmp_stat = [stat]
        for stat_type in tmp_stat:
            tmp_map += character.stats.find_of_type(stat_type)
        tmp_map += tmp_stat
        for tmp in tmp_map:
            if tmp not in stat_map:
                stat_map.append(tmp)
        # TODO: required to look at the damages table for mappings
        # ability.psyche[ StatType(name=psyche.name, ratio=psyche.ratio) ]
        for phobia in character.phobias.stats + character.disorders.stats:
            if not hasattr(phobia.unknown, 'action'):
                phobia.unknown['Action'] = ''
            action = phobia.unknown['Action']
            action = action.split() if '|' in action else [action]
            for a in action:
                if a in stat_map:
                    psyche_map.append(phobia)
        ability.psyche = psyche_map
        ability.unknown.update({'psyche_actions': tmp_map, })

    @staticmethod
    def ability_psychoses(interaction):
        """
        Build a one-time map of phobias and disorders related to an ability.

        :param interaction: Interaction, current interaction happening.
        :return: float, the multiplier required from psyche.
        """
        character = interaction.character.character
        ability = character.abilities.find(interaction.item)
        if not ability.psyche:
            PsycheHandler.build_psyche_map(interaction.character, ability)
        return PsycheHandler.psychoses_multiplier(interaction, ability)

    @staticmethod
    def understanding(target, source, emoting):
        """
        Define the understanding of a conversation piece from the targets
        perspective.

        :param target: PlayerCharacter, the person being interacted with.
        :param source: PlayerCharacter, the origin of the interaction.
        :param emoting: list, intention of the source actor.
        :return: list, the resulting emotions being acted by the source.
        """
        if (
                type(source) is not PlayerCharacter or
                type(target) is not PlayerCharacter
        ):
            return
        if not emoting:
            emoting = [0] * 6
        theatrical = target.character.abilities.find('Theatrical')
        capable = AbilityHandler.as_ability(theatrical)
        emotes = ['Humble', 'Extroverted', 'Thrifty', ]
        disorders = ['Stressed', 'Depressed', 'Psychotic', ]
        understood = []
        points = emotes + disorders
        for emote in points:
            data = [d for d in rpg_const.DAMAGE if d.name == emote][0]
            src = AbilityHandler.many_as_ability(
                data.functions, source.character)
            trg = AbilityHandler.many_as_ability(data.resistance, target)
            value = src.amount_draw - trg.amount_draw
            value += capable.amount_draw * emoting[points.index(emote)]
            if emote in disorders:
                value += sum([
                    source.disorders.find(emote).total,
                    target.character.disorders.find(emote).total
                ])
            understood.append(value)
        return understood

    @staticmethod
    def disorder_feedback(character, pivot_modifiers):
        """
        Update a PlayerCharacters psychological disorders from the phobias
        modifications passed while ensuring the damange resistances and
        assistives are equaly applied to the modifier for the disorders pivot.

        :param character: PlayerCharacter, psychology being applied to.
        :param pivot_modifiers: list, modifier to disorders of PlayerCharacter.
        """
        Middleware.handle('Disorder Feedback', character, pivot_modifiers)

    @staticmethod
    def phobia_feedback(character, pivot_modifiers):
        """
        Modify the phobias of the selected PlayerCharacter with the fedback
        PsychePivot objects, intention is to assert a single layer of update to
        the phobias and mapped disorders as a knock on effect from the
        PsychePivot applied.

        :param character: PlayerCharacter, psychology being applied to.
        :param pivot_modifiers: list, modifier to phobias of PlayerCharacter.
        """
        Middleware.handle('Phobia Feedback', character, pivot_modifiers)

    @staticmethod
    def interaction_feedback(interaction):
        """
        Provide a PlayerCharacter with the pivot changes as a response to the
        interaction passed.

        :param interaction: Interaction, the action completed.
        """
        ability = interaction.character.abilities.find(interaction.item)
        # TODO: Identify what form of pivot type was interacted.
        pivot_type = PsychePivot.TYPES['explored']
        # TODO: Requires refactoring the psyche_map of abilities.
        if ability:
            ability.time += interaction.timing
            if ability.time < 0:
                ability.time = 0
        phobias = []
        if not ability.psyche:
            actions = ability.unknown['psyche_actions']
            for phobia in interaction.character.phobias.stats:
                maps = phobia.action
                if type(maps) is not list:
                    maps = [maps]
                for map in maps:
                    if map in actions:
                        phobias.append(phobia)
            ability.psyche = phobias
        for psyche in ability.psyche:
            # TODO: Check in damages table how the feedback is applied.
            multiplier = pivot_type.ratio / len(
                psyche.action
                if type(psyche.action) is list else
                [psyche.action]
            )
            psyche.psyche.append(PsychePivot(
                type=pivot_type,
                duration=interaction.timing,
                multiplier=multiplier,
                target_to=interaction.character,
            ))
            psyche.total += interaction.timing * multiplier
        Middleware.handle('Character Feedback', interaction)


class ObjectHandler(RpgTick):
    """
    Manager class to handle objects and interactions between.
    """
    BUILTIN_ACTIONS = [
        'Manipulation', 'Movement', 'Impact', 'Medium', 'Theatrical',
        'Application',
        'Psy Charge',
    ]
    SOURCE_MAP = {}
    TARGET_MAP = {}

    @staticmethod
    def reset_affects(item):
        """
        Reset an items affects in preparation of transfer to another character.

        Additional use for this method instead of the described reset an object
        from being personalised, to reset a PlayerCharacter's model and have all
        affects removed from the body in one method. To ensure this is a valid
        option for use a 'reset' of the BodyPart objects of the PlayerCharacter
        needs to happen up front to store a duplciate of the original data.

        :param item: ObjectItem or BodyPart to reset affects to default.
        :return: the item passed as modified by this method.
        """
        modify = item
        if issubclass(item.__class__, ObjectItem):
            modify = item.item_model
        if 'affect_original' in modify.unknown.keys():
            original = modify.unknown['affect_original']
            modify.affect = original[:]
        else:
            modify.unknown['affect_original'] = modify.affect[:]
        if item.type.name == 'Construct':
            if 'contains_original' in modify.unknown.keys():
                original = modify.unknown['contains_original']
                modify.contains = duplicate_object(original)
            else:
                modify.unknown['contains_original'] = duplicate_object(
                    modify.contains)
        if 'affect_connections_original' in modify.unknown.keys():
            original = modify.unknown['affect_connections_original']
            non_construct = [
                a for a in modify.connections
                if (
                    a.type.name != 'Construct' and
                    a.group.name != 'Affect'
                )
            ]
            modify.connections = non_construct + original[:]
        if modify.connections:
            for connection in modify.connections:
                ObjectHandler.reset_affects(connection)
        return item

    @staticmethod
    def pattern_selection(target, select=None, pattern_index=None):
        rtn = []
        limit = sum([a.ratio for a in target.affect if a.name == 'Limit']) or 1
        pattern = [a.ratio for a in target.affect if a.name == 'Pattern'] or [1]
        if select < 1:
            select = 1
        if select and limit > select:
            limit = select
        pattern = pattern[0]
        if type(pattern) is str and '|' in pattern:
            pattern = pattern.split('|')
        else:
            pattern = [pattern]
        pattern_count = -1
        while len(rtn) < limit:
            pattern_count += 1
            if pattern_count >= len(pattern):
                pattern_count = 0
            p = pattern[pattern_count]
            if pattern_index and pattern_count != pattern_index:
                continue
            if pattern_count < len(target.contains.items):
                rtn.append(target.contains.remove(
                    target.contains.items[pattern_count], limit * p))
        return rtn

    @staticmethod
    def _duplicate_affect(affect):
        rtn = duplicate_object(affect, skip=['container'])
        rtn.container = duplicate_object(affect.container, skip=['items'])
        rtn.container.parent = rtn
        return rtn

    @staticmethod
    def connect(source, target, ability, interaction):
        """
        Make a connection between the character and the target, relevant
        limitations don't matter to the connection as mediums are assumed to
        span infinite space.

        :param source: PlayerCharacter or ObjectItem requiring a connection.
        :param target: PlayerCharacter or ObjectItem to be connected to.
        :param ability: Required ability to connect for.
        :param interaction: The interaction being applied due to the ability.
        :return MediumChannel or None
        """
        if type(ability) is not Stat or type(interaction) is not Interaction:
            return
        # TODO: Class typed arguments is a must post MVP.
        if issubclass(source.__class__, PlayerCharacter):
            source = source.character
        elif issubclass(source.__class__, ObjectItem):
            source = source.item_model
        if issubclass(target.__class__, PlayerCharacter):
            target = target.character
        elif issubclass(target.__class__, ObjectItem):
            target = target.item_model
        medium = AbilityHandler.ability_medium(ability)
        if not medium:
            return None
        if '|' in medium.item_model.requires:
            requires = medium.item_model.requires.split('|')
        else:
            requires = [medium.item_model.requires]
        matched = []
        source_function = None
        target_function = None
        for required in requires:
            if required in ObjectHandler.BUILTIN_ACTIONS:
                source_function = source
                target_function = target
            else:
                source_function = source.find_functions(
                    required, all_parts=True, in_children=True)
                if source_function:
                    source_function = source_function[0]
                target_function = target.find_functions(
                    required, all_parts=True, in_children=True)
                if target_function:
                    target_function = target_function[0]
            if not source_function or not target_function:
                break
            matched.append([source_function, target_function])
        if len(matched) != len(requires):
            return
        if medium not in source_function.connections:
            source_function.connections.append(medium.item_model)
        if medium not in target_function.connections:
            target_function.connections.append(medium.item_model)
        if source_function not in ObjectHandler.SOURCE_MAP.keys():
            ObjectHandler.SOURCE_MAP[source_function] = {medium: 1}
        else:
            ObjectHandler.SOURCE_MAP[source_function][medium] += 1
        if target_function not in ObjectHandler.TARGET_MAP.keys():
            ObjectHandler.TARGET_MAP[target_function] = {medium: 1}
        else:
            ObjectHandler.TARGET_MAP[target_function][medium] += 1
        return medium

    @staticmethod
    def disconnect(source, target, ability=None):
        """
        Remove a connection between a source and a target while
        accounting for other targets being connected by the same
        PlayerCharacter.

        :param source: PlayerCharacter or ObjectItem to be disconnected.
        :param target: PlayerCharacter or ObjectItem to be disconnected from.
        :param ability: Ability to disconnect, default is None and remove all.
        """
        source_map = None
        target_map = None
        # TODO: Class typed arguments is a must post MVP.
        if issubclass(source.__class__, PlayerCharacter):
            source = source.character
        elif issubclass(source.__class__, ObjectItem):
            source = source.item_model
        if issubclass(target.__class__, PlayerCharacter):
            target = target.character
        elif issubclass(target.__class__, ObjectItem):
            target = target.item_model
        if ability:
            mediums = [AbilityHandler.ability_medium(ability)]
        else:
            mediums = [
                m for m in source.connections
                if m in target.connections and m.group.name == 'Medium'
            ]
        if not mediums:
            return None
        if source in ObjectHandler.SOURCE_MAP.keys():
            source_map = ObjectHandler.SOURCE_MAP[source]
        if target in ObjectHandler.TARGET_MAP.keys():
            target_map = ObjectHandler.TARGET_MAP[target]
        for medium in mediums:
            if source_map and medium in source_map.keys():
                source_map[medium] -= 1
                if source_map[medium] == 0:
                    source.connections.remove(medium.item_model)
            if target_map and medium in target_map.keys():
                target_map[medium] -= 1
                if target_map[medium] == 0:
                    target.connections.remove(medium.item_model)

    @staticmethod
    def can_interact(part, object_item, *args):
        """Check if the two objects are able to interact with each other."""
        able = False
        if not args or not part or not object_item:
            return able
        root = part.find_root()
        body_parts = root.find_name(part.name)
        # Confirmation the BodyPart and ObjectItem can interact
        actions = part.actions
        if type(actions) is str:
            actions = [actions]
        for action in actions:
            if (
                action in object_item.actions or
                action in object_item.item_model.requires
            ):
                able = True
        # Confirm the action desired is available from the item
        if able and object_item.item_model.find_functions(args[0]):
            able = True
        if not able:
            able = args[0] in ObjectHandler.BUILTIN_ACTIONS
        return able

    @staticmethod
    def externalise_model(item_model, source, speed=0):
        Middleware.handle('Position Vector', source)
        if type(item_model) is not BodyPart:
            return None
        item = ObjectItem()
        item.item_model = item_model
        item.vector = duplicate_object(source.vector, default=BodyVector())
        item.vector.speed = speed
        return item

    @staticmethod
    def externalise_waste(waste, source):
        """
        Add radiation effects from wasted energy spent on interactions.

        TODO: Add `default=None` argument to have a default for items.

        :param waste: number, the amount of waste produced.
        :param source: BodyPart, producing waste.
        :return: list of waste products.
        """
        wastage = [a for a in source.affect if a.name == 'Waste']
        if not waste or not wastage:
            return []
        output = []
        rtn = []
        for waste in wastage:
            if type(waste) is StatType:
                output.append(waste)
            elif type(waste) is str:
                waste_list = waste.split('|')
                add_list = []
                for waste_output in waste_list:
                    waste_output = waste_output.split(':')
                    ratio = float(waste_output[1]) if len(waste_output) else 1
                    add_list.append(StatType(waste_output[0], ratio=ratio))
                output += add_list
        for waste_out in output:
            model = search_effect(waste_out.name, cache=True)
            energy = search_effect(
                model.contains.restrict[0], cache=True)
            energy.quantity = int(waste) * waste_out.ratio
            model.contains.add(energy)
            rtn.append(ObjectHandler.externalise_model(model, source))
        return rtn

    @staticmethod
    def item_connected_health(item):
        """
        Aggregate the health value of an item from the parts connected to.

        :param item: the parent BodyPart needing the health aggregated for.
        :return: float, float
        """
        flat = item.flatten_from()
        flat.remove(item)
        flat = [f for f in flat if f.group.name not in ['Medium']]
        max = 0
        health = 0
        for item in flat:
            if item.health_max:
                max += item.health_max
                health += item.health
        return max, health

    @staticmethod
    def _process_spread(ratio, item, part):
        """
        Transfer an amount of an affect from on item to a BodyPart

        :param ratio: float, amount to transfer.
        :param item: the item transferring spread affects to the body part
        :param part: body part being impacted on.
        """
        # TODO: Place `spread_types` list in a configuration
        # TODO: Add damage reactives to parts to activate applied affects.
        spread_types = [
            'Pharmaceutical', 'Bacterial', 'Phage', 'Poison', 'Toxin',
            'Radiation', 'Cancer', 'Nanotech', 'Acid', 'Alkaline',
            'Strength', 'Reflex', 'Endurance', 'Metabolism', 'Looks', 'Luck',
            'Dexterity', 'Willpower', 'Belief', 'Intelligence', 'Charm',
            'Psychic',
            'Metabolism', 'Regeneration', 'Immune', 'Fertility',
            'Circulation', 'White Blood Cells', 'Platelets',
        ]
        item_affects = [
            p for p in item.connections
            if p.group.name == 'Affect' and p.type.name in spread_types
        ]
        remove = []
        for affect in item_affects:
            if affect.type.name == 'Construct':
                amount = ceil(affect.container.quantity_remaining() * ratio)
                if not amount:
                    continue
                removed = affect.container.remove(quantity=amount)
                new_affect = ObjectHandler._duplicate_affect(affect)
                new_affect.container.add(removed)
                part.connections.append(new_affect)
                if not affect.container.quantity_remaining():
                    remove.append(affect)
            else:
                amount = ceil(affect.health * ratio)
                if amount < affect.health:
                    new_affect = ObjectHandler._duplicate_affect(affect)
                    new_affect.health = amount
                else:
                    new_affect = affect
                part.connections.append(new_affect)
                if affect.health <= 0:
                    remove.append(affect)
        for connection in remove:
            item.connections.remove(connection)

    @staticmethod
    def _process_impact_spread(velocity, energy, item, part):
        """
        Manage the transfer of spread affects from an Impact objectItem with
        the part of the character performing checks into the expected amount
        transferred into the part depending on the Impact duration defined from
        the velocity of the Impact.

        Expected running of this function is post the health and energy check
        giving this the 'leave behind' task to the part impacted.

        :param velocity: float, length of time the transfer has to take.
        :param energy: float, expectation to retain all transfer under 0.
        :param item: the item transferring spread affects to the body part
        :param part: body part being impacted on.
        """
        weight = part.weight or 1
        time = velocity / weight * rpg_const.AVERAGE_KILO_VOLUME
        ratio = 1 if not energy else time / rpg_const.TIME_STEP
        ObjectHandler._process_spread(ratio, item, part)

    @staticmethod
    def _process_impact(
            energy, accuracy, item, part, part_is_character=False
    ):
        """
        Manage the interactions between item and part of body or
        worn parts on the body.

        :param item: The item interacting with the body.
        :param part: The body part or worn item being Impacted on.
        :return float of the remaining Impact value.
        """
        Middleware.handle('Impact Part Pre', energy, accuracy, item, part)
        part_accuracy_affects = [
            p for p in part.find_functions('Accuracy', all_parts=True)
            if p.group.name == 'Affect'
        ]
        resist_accuracy = 0
        remaining = accuracy
        for affect in part_accuracy_affects:
            if affect.type.name == 'Construct':
                if not affect.container.quantity_remaining():
                    continue
                # TODO: Match the damage being delt by the item with the available resistances of the Construct and provide an amount of interaction expected from the Construct affects to be removed from the energy container of the construct.
                removed = affect.container.remove(quantity=remaining)
                resist_accuracy += removed.quanitity
            else:
                if affect.health <= remaining:
                    resist_accuracy += affect.health
                    affect.health = 0
                else:
                    resist_accuracy += remaining
                    affect.health -= remaining
            remaining = accuracy - resist_accuracy
        accuracy = remaining
        if accuracy <= 0:
            return energy, 0
        if accuracy > 1:
            accuracy = 1
        else:
            random_accuracy = random() * (1 - accuracy)
            accuracy += random_accuracy
        item_energy = mass_to_energy(item.weight or 1)
        total_hit = energy * item_energy * accuracy
        resist_hit = 0
        remaining = total_hit
        part_affects = [
            p for p in item.find_functions('Impact', all_parts=True)
            if p.group.name == 'Affect'
        ]
        # Remove Impact from part affects before Impact of part.
        part_energy = mass_to_energy(part.weight or 1) / part.health_max
        for affect in part_affects:
            if affect.type.name == 'Construct':
                if affect.container.quantity_remaining():
                    removed = affect.container.remove(
                        quantity=int(remaining / part_energy))
                    resist_hit += removed.quanitity
            elif affect.type.name == 'Protection':
                if affect.health * part_energy < remaining:
                    resist_hit += affect.health * part_energy
                    affect.health = 0
                else:
                    resist_hit += remaining
                    affect.health -= int(remaining / part_energy)
            remaining = total_hit - resist_hit
        # Impact hits part and reduces any remaining.
        if part_is_character:
            if part.health * part_energy < remaining:
                resist_hit += part.health * part_energy
                part.health = 0
            else:
                resist_hit += remaining
                part.health -= int(remaining / part_energy)
        Middleware.handle('Impact Part Post', resist_hit, item, part)
        return total_hit - resist_hit, accuracy

    @staticmethod
    def _process_success(action, interaction, form='ms'):
        """
        Process and return the success of the ability being used through the
        applied calculations of associated indicators and any distance concerns
        expected from performing an action at distance.

        If a value for `form` is not passed as expected the default will be
        assigned and used automatically.

        :param action: str, The ability being used to perform this action.
        :param interaction: Interaction, current interaction being processed.
        :param form: str, ['ms', 'draw'] are the correct values to pass
        :return: float, the success rate of this ability.
        """
        if form not in ['ms', 'draw']:
            form = 'ms'
        ability = interaction.character.abilities.find(action)
        AbilityHandler.as_ability(ability, interaction)
        skill = ability.unknown['Skill']
        skill = interaction.character.skills.find(skill)
        stats = skill.unknown['Stat']
        drawing = []
        if type(stats) is str:
            if '|' in stats:
                stats = stats.split('|')
            else:
                stats = [stats]
        for stat in stats:
            stat = interaction.character.stats.find(stat)
            drawing += [d for d in stat.draw if d.name != interaction.name]
        success = []
        expected = []
        for other in drawing:
            expect = getattr(
                interaction, '{}_{}'.format(other.name.lower(), format), 1)
            if form == 'ms':
                expect *= RpgTick.DIFF
            expect *= other.ratio / len(stats)
            expected.append(expect)
            other_ind = interaction.character.indicator(other.name)
            success.append(other_ind.draw(expect))
        # Distance check has already been gotten from external.
        distance_ratio = (
            AbilityHandler.distance_difficulty(ability, interaction)
            if not interaction.distance_ratio else
            interaction.distance_ratio
        )
        return ((sum(success) or 1) / (sum(expected) or 1)) * distance_ratio

    @staticmethod
    def interaction_affects(action, interaction):
        """
        Health and regeneration of the body.

        Identifying available 'Affect' objects of the body in interaction
        and start the healing process, once this process has started there
        is no way to turn it off until the body is dead.

        This ability can only be applied once per body as all effects
        attributed to healing the body are accounted for at once.

        Indicator Affects:
        Restrict application of other modifications to stats as top level
        to the character as a means to punish the user for using an ability
        while not retarding the effectiveness as a whole. Put another way,
        when you're resting your reflexes are reduced, likewise when
        energising yourself your requirements for having the ability active
        will reduce your nimbleness of mind to react to your surroundings.

        Healing Affects:
        Each healing affect is capable of applying benefits to the health
        value of the BodyPart directly as well as supplemental affects in
        accordance to the type of damage being applied to: Bacterial for
        Organic, Oxidise for Mechanical, Melt for Circuitry. Each type of
        health cannot be intermixed but supply supplemental affects to the
        other part: Bacterial applied to Circuitry does not change the
        health but can induce a spreading effect of the affect.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        modifiers = rpg_const.DAMAGE_MODIFIERS
        functions = rpg_const.DAMAGE_FUNCTIONS
        indicators = rpg_const.DAMAGE_INDICATORS
        health = rpg_const.DAMAGE_HEALTH

        def modify_health(part, value):
            """
            BodyPart calculation determining the amount of health to be
            taken off.

            :param part: BodyPart to have affected with the value.
            :param value: amount of health to be removed from the BodyPart.
            :return: float, the value modified of the BodyPart.
            """
            value *= float(part.circulation) + sum([
                a.total for a in part.affect
                if a.name == 'Circulation'
            ])
            if value + part.health < 0:
                value = part.health
            if value + part.health > part.health_max:
                value = part.health_max - part.health
            part.health += value
            return value

        def find_children(part, id='health'):
            """
            Find child connections applicable for modification of a value,
            by default 'Health' is the only check.

            :param part: BodyPart to find child objects from.
            :param id: str, type of check to make against BodyPart objects.
            :return: list, of BodyPart objects.
            """
            if id == 'health':
                if part.health and part.health < part.health_max:
                    return part
            return [
                find_children(p, id=id)
                for p in part.connections
                if p and p is not part and type(p) is BodyPart
            ]

        items = interaction.part.find_group('Affect')
        for item in items:
            part = item.parent
            id = item.functions[0]
            others = [a for a in item.affect if a.name != id]
            value = sum([a for a in item.affect if a.name == id])
            value *= RpgTick.DIFF
            if id in indicators:
                # Manage the indicators
                indicator = interaction.character.indicator(id)[0]
                if not indicator:
                    continue
                allocated = indicator.pool(value)
                for mod in others:
                    stat = interaction.character.stats.find(
                        mod.name, auto_create=False)
                    if mod not in stat.modifiers:
                        if allocated:
                            stat.modifiers.append(mod)
                    elif not allocated:
                        stat.modifiers.remove(mod)
                continue
            children = find_children(part, id=id)
            spread = 1 / len(children) if len(children) > 0 else 1
            value *= spread
            for child in children:
                if id in health:
                    # Circulation is a ratio of spread from part to part.
                    heal_for = [
                        h for h in rpg_const.DAMAGE if h.name == id][0]
                    if heal_for.type.name == child.manufacturer:
                        modify_health(child, value)
                elif id in modifiers:
                    others += [a for a in item.affect if a.name == id]
                for mod in others:
                    found = False
                    affect_for = [
                        h for h in rpg_const.DAMAGE if h.name == mod.name
                    ][0]
                    if affect_for.type.name != child.manufacturer:
                        continue
                    c_list = list(
                        child.functions
                        if mod.name in functions else child.affect)
                    for affect in c_list:
                        if affect.name == mod.name:
                            found = True
                            if mod.name not in affect.modifiers:
                                affect.modifiers.append(mod)
                            elif mod in affect.modifiers:
                                affect.modifiers.remove(mod)
                    if not found:
                        affect = StatType(name=mod.name, ratio=0)
                        affect.modifiers.append(mod)
                        c_list.append(affect)
        # Run through body affects and find `modifiers` that affect health
        flat = [
            p for p in interaction.part.flatten_from() if p not in items]
        for part in flat:
            value = sum([
                a.total for a in part.affect
                if a.name in modifiers and a.name in health
            ]) * RpgTick.DIFF
            modify_health(part, value)

    @staticmethod
    def interaction_impact(action, interaction):
        """
        An ObjectItem or PlayerCharacter has imacted another object, this
        results in a one way contact interaction and does not take into
        consideration (nor should it) the origin type impacting. Allows the
        agnostic transfer of energy from one thing to another.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        velocity_0 = 0
        velocity_152 = 0
        Middleware.handle('Distance KM', interaction)
        for affect in interaction.item.item_model.affect:
            if affect.name == 'Velocity 0':
                velocity_0 = float(affect.ratio)
            elif affect.name == 'Velocity 152.4':
                velocity_152 = float(affect.ratio)
        velocity = impact_velocity(
            interaction.distance_km, velocity_0, velocity_152)
        energy = impact_energy(interaction.item.weight, velocity)
        Middleware.handle('Impact Energy', interaction, energy)
        impact_chain = [
            item
            for item in interaction.part.list_wears(in_children=True)
            if item.find_functions(action, all_parts=True)
        ]
        impact_chain.append(interaction.part)
        item_affects = [
            p for p in interaction.item.find_functions(
                'Impact', all_parts=True)
            if p.group.name == 'Affect'
        ]
        # Additional health affects from impact
        impact_affect = sum([
            a.ratio
            for af in item_affects
            for a in af.affect
            if a.name == 'Health'
        ])
        through = energy + impact_affect
        accuracy = (
            AbilityHandler.distance_ratio(interaction.item.meta_ability)
            if not interaction.item.meta_ability.distance_ratio else
            interaction.item.meta_ability.distance_ratio
        )
        for connection in impact_chain:
            is_char = bool(
                impact_chain.index(connection) == len(impact_chain) - 1)
            # TODO: weight/volume to velocity/area ratios determin the depth of penetration for an impact between a body and an item: a weight/volume ratio higher than the other impact would result in 'blunt' damage. This is a game and only expected to simulate the impact type, melee impacts slicing through a part is expected considering no armoured parts.
            through, accuracy = ObjectHandler._process_impact(
                through, accuracy, interaction.item, connection, is_char)
            energy_diff = energy - through
            velocity = sqrt(energy_diff / interaction.item.weight * 2)
            ObjectHandler._process_impact_spread(
                velocity, through, interaction.item, connection)
        energy = through - impact_affect
        Middleware.handle('{} Through'.format(action), interaction, energy)

    @staticmethod
    def interaction_reload(action, interaction):
        """
        Use a manipulator body part to find a filled container to fit into
        the object being used, the container with the closest to max is
        chosen first with a minor adjustment of reload ability amount_draw
        compared to a min value. Management of magazines or feeding containers
        in an item is being passed from item to hand and then to pocket is not
        expected here instead the supply of the statistics expected from this
        character is and delivered to the host application through the
        Middleware function callbacks.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        character = interaction.character
        if interaction.targets is not character:
            character = interaction.targets
        reload_containers = interaction.item.find_functions('Reload')
        if not character.torso:
            Middleware.handle('Reload Disabled', interaction)
            return
        ability = interaction.character.abilities.find(interaction.item)
        AbilityHandler.as_ability(ability, interaction)
        reload_time = 0
        reload_time_min = 0
        for reloading in reload_containers:
            has_reloadable = character.torso.find_packed(reloading.name)
            if not has_reloadable:
                Middleware.handle('Reload Empty', reloading, interaction)
                return
            reload_time += sum(
                [a.ratio for a in reloading.affect if a.name == 'Reload'])
            reload_time_min += sum(
                [a.ratio for a in reloading.affect if a.name == 'Reload Min'])
            # find the fullest magazine
            flat_refills = [
                choice(refill) if type(refill) is list else refill
                for refill in has_reloadable.values()
            ]
            # select the fullest and find the container in reverse
            flat_refills = sorted(
                [r for r in flat_refills if r.contains.quantity],
                key=lambda x: x.quantity, reverse=True
            )
            if not flat_refills:
                Middleware.handle('Reload Empty', reloading, interaction)
                return
            flat_refills = flat_refills[0]
            refill_container = None
            for container in has_reloadable.keys():
                lst = has_reloadable[container]
                if type(lst) is not list:
                    lst = [lst]
                if flat_refills in lst:
                    refill_container = container
            Middleware.handle(
                'Reload Container', flat_refills, reloading, refill_container,
                interaction
            )
        # update the interaction with the expected time to process reload
        interaction.action_frames += reload_time - interaction.amount_draw
        if interaction.action_frames < reload_time_min:
            interaction.action_frames = reload_time_min
        Middleware.handle('Reload Active', interaction)

    @staticmethod
    def interaction_holster(action, interaction):
        """
        Holster a weapon away for a character.
        This will initiate the start process of the holstering and keep a time
        to the valid ticks processig this interaction, when the timing runs out
        the items (if any) are removed from the manipulator body part.

        NOTE: There is no direct reference to miss ticks through this process
        thus a custom management to identify if there are any animation slips
        between the expected initial timing value and the now comparted to the
        start value of the interaction.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        part = interaction.targets
        item = interaction.part
        pack_loc = interaction.item
        max_time = rpg_const.TIME_ACTION_HOLSTER
        if not item:
            action = 'Focusing'
            max_time = rpg_const.TIME_ACTION_FOCUSING
            ability = interaction.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
        elif item.type.name == 'Construct':
            action = 'Future Tactiatian'
            max_time = rpg_const.TIME_ACTION_FUTURE_TACTITIAN
            ability = interaction.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
        else:
            ability = interaction.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
        if not interaction.start:
            interaction.start = RpgTick.CURRENT
            interaction.timing = max_time - interaction.amount_draw
            if interaction.timing < 0:
                interaction.timing = 0
            interaction.action_frames = interaction.timing
            Middleware.handle('{} Ready'.format(action), interaction)
            return
        elif interaction.timing > 0:
            interaction.timing -= RpgTick.DIFF
            return
        if item.type.name == 'Construct':
            part.contains.remove(item)
        elif item:
            part.contains.remove(item)
            pack_loc.contains.add(item)
        Middleware.handle('{} Finish'.format(action), interaction)

    @staticmethod
    def interaction_unholster(action, interaction):
        """
        Ready yourself with the selected tools and weapons for manipulation.

        Constructs of psychic abilities being unholstered are supplied as the
        expected container and requires no transfer of object model from a
        container to the manipulator.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        if interaction.start:
            return
        max_time = rpg_const.TIME_ACTION_UNHOLSTER
        container = interaction.item
        if not container:
            action = 'Focusing'
            max_time = rpg_const.TIME_ACTION_FOCUSING
            ability = interaction.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
        elif container.type.name == 'Construct':
            action = 'Future Tactiatian'
            max_time = rpg_const.TIME_ACTION_FUTURE_TACTITIAN
            ability = interaction.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
            interaction.part.contains.add(container)
        else:
            ability = interaction.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
            item = container.remove()
            interaction.part.contains.add(item)
        interaction.start = RpgTick.CURRENT
        interaction.timing = max_time - interaction.amount_draw
        if interaction.timing < 0:
            interaction.timing = 0
        interaction.action_frames = interaction.timing
        Middleware.handle('{} Ready'.format(action), interaction)

    @staticmethod
    def interaction_throw(action, interaction):
        """
        An object is being thrown by a manipulator and requires the object to
        be investigated to identify the correct ability being used against the
        object and have the the object externalised from the model format.

        Using the ObjectItem's project function as a basis the throw action
        can modify the process to handle externalisation.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        if not interaction.item:
            return
        if type(interaction.item) is not ObjectItem:
            item = ObjectItem()
            item.item_model = interaction.item
        else:
            item = interaction.item
        Middleware.handle('Position Vector', interaction.part)
        vector = interaction.part.vector
        if not vector:
            Middleware.handle('Position Vector', interaction.character)
            vector = interaction.character.vector
        item.vector = duplicate_object(vector, default=BodyVector())
        item.meta_ability = interaction
        accuracy = (
            AbilityHandler.distance_ratio(item.meta_ability)
            if not item.meta_ability.distance_ratio else
            item.meta_ability.distance_ratio
        )
        ratio = 1
        if item.group.name in ['Telekinesis']:
            psy_act = AbilityHandler.as_ability(
                interaction.character.abilities.find(item.group.name)
            )
            ratio = psy_act.accustomed
        primable = item.find_functions('Prime')
        if primable:
            ability = interaction.character.abilities.find('Grenade Priming')
            accustomed = AbilityHandler.as_ability(ability).accustomed
            if accustomed > rpg_const.GRENADE_ACCUSTOMED_THREASHOLD:
                interaction.character.interact(interaction.part, 'Prime')
        for affect in item.item_model.affect:
            if affect.name == 'Velocity 0':
                item.vector.speed = float(affect.ratio) * ratio
        # TODO: Process accuracy through a vector modification utility.
        Middleware.handle('Throw Accuracy', item, accuracy)

    @staticmethod
    def interaction_psy_charge(action, interaction):
        """
        Charge an ObjectItem or a PlayerCharacter with Psychic energy which
        is normally transacted with the energy item Psytron.

        As a basic MVP application of charging 'Psy Charge' is being kept
        separate from other forms of charging: battery to circuit, as there
        is already a Feed and Receive mechanism in place which can deal
        with this eventuality.

        This form of charging is specific to reducing a value from an
        indicator and providing to the target or drawing from a battery
        and charging an indicator, the source of the indicator does not
        matter.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        pair = [interaction.part, interaction.item]
        Middleware.handle('Distance KM', interaction)
        if type(pair[0]) is Indicator:
            source_ind = interaction.part
            ability = source_ind.character.abilities.find(action)
            AbilityHandler.as_ability(ability, interaction)
        total_charging = 0
        for interaction in interaction.part.character.interactions:
            if interaction.action == 'Psy Charge':
                total_charging += 1
        if total_charging == 0:
            Middleware.handle('Psy Charge Nope', interaction)
            return
        primary = interaction.amount_ms * RpgTick.DIFF / total_charging
        if primary == 0:
            Middleware.handle('Psy Charge Nope', interaction)
            return
        elif primary < 0:
            pair = pair.reverse()
            primary *= -1
        if type(pair[0]) is Indicator:
            success = ObjectHandler._process_success(action, interaction)
            primary = pair[0].draw(primary * success)
            psytron = search_effect('Psytron', cache=True)
            psytron.quantity = int(primary / rpg_const.IMBUING_ENERGY_RATIO)
            primary = psytron
        elif type(pair[0]) is ItemContainer:
            valid = pair[0].parent.find_functions(action, in_children=False)
            if valid:
                primary = pair[0].remove('Psytron', quantity=int(primary))
            else:
                primary = None
                Middleware.handle('Psy Charge No Source', interaction)
        else:
            primary = None
            Middleware.handle('Psy Charge No Source', interaction)
        if primary and primary.quantity > 0:
            stop = 0
            if type(pair[1]) is Indicator:
                value = primary.quantity * rpg_const.IMBUING_ENERGY_RATIO
                pair[1].pool(int(value))
            elif type(pair[1]) is ItemContainer:
                valid = pair[1].parent.find_functions(
                    action, in_children=False)
                if valid:
                    if pair[1].quantity > pair[1].quantity_max:
                        stop = pair[1].quantity - pair[1].quantity_max
                        primary.quantity -= stop
                    pair[1].add(primary)
                    if stop > 0:
                        stop_rtn = duplicate_object(primary)
                        stop_rtn.quantity = stop
                        if type(pair[0]) is ItemContainer:
                            pair[0].add(stop_rtn)
                else:
                    Middleware.handle('Psy Charge No Target', interaction)
            else:
                Middleware.handle('Psy Charge No Target', interaction)
        else:
            Middleware.handle('Psy Charge No Charge', interaction)

    @staticmethod
    def interaction_construct(action, interaction):
        """
        Manifest a Psychic object into the world.

        Independent from the charging of a psychic ability effect is
        manifesting Construct's into the physical world.

        For a manifestation to be brought into existence the proper amount
        of energy is required to create the initial construct, without a
        soul bound to the construct the capability of this object is only
        for physical attacks. A construct with the correct number of soul
        slots will allow the construct to be self aware and allow abilities
        to occur, including self charging through psychic means depending
        on the soul's ability to be naturally psychic and trained.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        if not interaction.part or not interaction.part.contains:
            return
        required = sum([
            c.contains.quantity_max
            for c in interaction.part.connections
            if c.type.name in ['Construct']
        ])
        primary_ind = interaction.character.indicator(interaction.name)
        if required > primary_ind.value / rpg_const.IMBUING_ENERGY_RATIO:
            return
        Middleware.handle('Distance KM', interaction)
        success = ObjectHandler._process_success(
            action, interaction, form='draw')
        # Drawing all from indicator as the value is for draw not ms
        # TODO: amount_draw will increase with level up this will draw more from an indicator the higher the level of the character
        primary = primary_ind.draw(
            interaction.amount_draw) / rpg_const.IMBUING_ENERGY_RATIO
        if interaction.part.contains:
            for connection in interaction.part.connections:
                if connection.type.name not in ['Construct']:
                    continue
                manifesting = duplicate_object(connection)
                manifesting.quantity = 1
                energy = interaction.part.contains.remove(
                    'Psytron', manifesting.contains.quantity_max * success)
                try:
                    interaction.part.contains.add(manifesting)
                    manifesting.contains.add(energy)
                except Exception:
                    waste = interaction.part.contains.add(energy)
                    Middleware.handle('Waste Energy', waste)
                waste = interaction.part.contains.remove(
                    'Psytron',
                    manifesting.contains.quantity_max * (1 - success)
                )
                Middleware.handle('Waste Energy', waste)

    @staticmethod
    def interaction_bind_soul(action, interaction):
        """
        Apply a soul into a Construct.

        A binding requires energy to manifest a soul into a physical
        vessel where the soul is given life through the construct for a
        period of time determined from the energy available to the binding
        body part.

        The drain of energy required of the binding is equal to that
        demanded from the indicator of the Construct's creator, this
        requires the binding ability to be charged and continually powered
        for the bind to sustain itself, otherwise the drain is only taken
        from the Construct and destroy itself.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        pass

    @staticmethod
    def interaction_imbue(action, interaction):
        """
        Imbue something with affects using a divined soul.

        Place a 'Construct Affect' onto a physical or construct object, each
        imbuing on a object requires additional energy to have placed onto
        allowing a character with a huge pool of energy to draw from to add
        many affects onto an item.

        Applying an Imbuing requires nothing more than focus but is greatly
        augmented by the use of tools connected to Psychic Generators.

        This method is expected to run per millisecond, energy transferred
        is reliant on the circulation or natural ability of the
        PlayerCharacter using the imbuing tool.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        source = interaction.part
        imbue_effects = source.find_functions(action)
        apply_effects = [
            e for e in imbue_effects.connections
            if e.group.name == 'Affect'
        ]
        source_energies = source.find_type('Battery', all_parts=True)
        energy_available = sum([
            b.contains.quanity for b in source_energies])
        energy_rate = 0
        accustomed = 0
        if interaction.character:
            abilities = interaction.character.character.abilities
            energy_rate = AbilityHandler.as_ability(
                abilities.find(action)).amount_ms
            accustomed = AbilityHandler.as_ability(
                abilities.find(action)).accustomed
        if accustomed < 1:
            accustomed = 1
        energy_rate = max(energy_rate, rpg_const.IMBUING_ENERGY_RATIO)
        target = interaction.item
        circulation = float(source.circulation)
        per_ms = RpgTick.DIFF * energy_rate * circulation
        filled = sum([
            b.contains.quanity
            for b in target.find_group('Affect', all_parts=True)
        ])
        fill_max = sum([
            b.contains.quanity_max
            for b in target.find_group('Affect', all_parts=True)
        ])
        max_rate = (
            mass_to_energy(target.weight) *
            rpg_const.IMBUING_ENERGY_RATIO *
            accustomed
        )
        fill_max = min(max_rate, fill_max, energy_available)
        if fill_max - filled < per_ms:
            per_ms = fill_max - filled
        temporary_container = ItemContainer(max_weight=1000000)
        for src_energy in source_energies:
            transfer = src_energy.contains.remove(per_ms)
            temporary_container.add(transfer)
        waste = 0
        added = []
        names = [c.name for c in target.connections]
        for affect in apply_effects:
            if affect.name not in names:
                add = duplicate_object(affect)
                added.append(add)
                target.connections.append(add)
                affect.contains.items = []
                affect.parent = target
            effect = [
                c for c in target.connections if c.name == affect.name][0]
            i = temporary_container.quantity / len(apply_effects)
            if circulation < 1:
                waste += i * (1 - circulation)
                i -= i * (1 - circulation)
            waste += i - int(i)
            effect.container.add(temporary_container.remove(int(i)))
        if 'affect_original' in target.unknown.keys():
            target.unknown['affect_original'] += added
        ObjectHandler.externalise_waste(waste, source)

    @staticmethod
    def interaction_cleansing(action, interaction):
        """
        Clean an object of affects.

        Remove an amount of an affect from an object, for affects which have
        no energy remaining on them will have the affect removed completely.

        This cleansing action will only operate on 'Construct Affect'
        objects as these are constructs from a psychic medium instead of
        the physical world.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        target = interaction.part
        if target.type.name == 'Construct' or target.group.name == 'Affect':
            Middleware.handle('Cleansing Failure', interaction)
            return
        character = interaction.character
        imbued = target.find_imbued(None)
        ability = AbilityHandler.as_ability(
            character.abilities.find(action))
        max_rate = ability.energy_ms * RpgTick.DIFF
        waste = 0
        # TODO: Cleanse an Imbue effect of selected connections
        for affect in imbued:
            value = int(max_rate / len(imbued))
            removed = affect.contains.remove(value)
            if affect.contains.quantity < 1:
                affect.parent.connections.remove(affect)
            if removed.quantity < value:
                waste += value - removed.quantity
        ObjectHandler.externalise_waste(waste, target)

    @staticmethod
    def interaction_imbue_select(action, interaction):
        """
        Change what you want to imbue on an object.

        Apply an affect onto an affect which is applicable to the Imbue
        action, without an appropriate affect to apply elsewhere an Imbue
        affect is useless and will fail the imbuing.

        Applying multiple affects onto an item at the same time requires
        that same number of Imbue effects applied to the imbuing tool, as
        example: 'Psyfiller One🏵' has capacity for 1 imbuing effect at a
        time.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        target = interaction.part
        affects = interaction.item
        independant = set()
        apply = []
        for affect in affects:
            if (
                    affect.name in independant or
                    affect.group.name != 'Affect' and
                    affect.type.name != 'Construct'
            ):
                continue
            independant.add(affect.name)
            affect = duplicate_object(affect)
            CharacterHandler.personalise(affect, interaction.character)
            apply.append(affect)
        if not apply:
            Middleware.handle('Imbue Select Failed', interaction)
            return
        imbue_effects = target.find_functions('Imbue')
        applied = []
        for effect in imbue_effects:
            # One Imbuing affect per Imbue function on this target object
            imbue = apply[0] if len(apply) else None
            if not imbue:
                break
            found = [c for c in effect.connections if c.name == imbue.name]
            if not found:
                effect.connections.append(imbue)
            applied.append(imbue)

    @staticmethod
    def interaction_communication(action, interaction):
        """
        Communication channel.

        Receive from a MediumChannel object type to allow conversation to be
        a two or more way system rather than just interact and feedback.

        Relative responses should be provided as selections of conversation
        to be used in sequence provided from user feedback as a way to
        manage a conversation. All responses are stored on a PlayerCharacter
        object through inspection of a conversation data set.

        Leverage required to enter a particular arch of a conversation is
        expected to be applied after the 'emoting' series of values are
        supplied, this way multiple leverage points can be demanded as a
        requirement before the conversation option is a success.
        Example from MVP: "0|0|0|0|0|1|Sex Tape (Animal Farm)"

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        target = interaction.part
        source = interaction.character
        item = interaction.item
        if interaction.item and type(interaction.item) is list:
            if type(interaction.item[0]) not in [str, int, float]:
                item = interaction.item[0]
                emoting = interaction.item[1:]
            else:
                emoting = interaction.item[:]
        else:
            emoting = [0] * 6
        understanding = PsycheHandler.understanding(target, source, emoting)
        match = []
        i = -1
        while i < len(understanding):
            i += 1
            req = float(item.requires[i])
            if req < 0:
                match.append(1 if req >= understanding[i] else 0)
            else:
                match.append(1 if req <= understanding[i] else 0)
        if sum(match) < len(understanding):
            Middleware.handle(
                'Communication Failed', item, understanding, interaction)
            return
        # Is all leverage required from the source known to this character?
        required = item.requires[6:]
        if required:
            leverage = target.character.leveraged
            found = []
            for req in required:
                name = req.split(':')[0]
                value = sum(req.split(':')[1:])
                possible = [l for l in leverage if l.related.name == name]
                if possible:
                    possible = [
                        l for l in leverage
                        if value < l.aware_from(source)
                    ]
                    found += possible
            if not found:
                Middleware.handle(
                    'Communication Failed Leverage',
                    item,
                    understanding,
                    interaction
                )
                return
        # Ensure the external system is aware of conversation supply
        # everything identified and expect the conversation to be continued
        # through the MediumChannel again.
        Middleware.handle(
            'Communication Success',
            item,
            understanding,
            interaction,
            [c for c in item.connections if type(c) is not str]
        )
        for action in interaction.actions:
            followup = Interaction(target, None, None, action)
            followup.targets = [source]
            followup.tracker = interaction.tracker
            interaction.medium.interact(followup)

    @staticmethod
    def interaction_leverage(action, interaction):
        """
        Process the leverage incoming to the PlayerCharacter.

        Provide the target of the leverage a pivot in psychology as long as
        the required understanding from the source's delivery is accepted
        to manage the leverage in that character.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        item = interaction.item
        target = interaction.part
        source = interaction.character
        if type(interaction.item) is list:
            item = interaction.item[0]
            emoting = interaction.item[1:]
        else:
            emoting = [0] * 6
        understanding = PsycheHandler.understanding(target, source, emoting)
        match = []
        i = -1
        while i < len(understanding):
            i += 1
            req = float(item.requires[i])
            if req < 0:
                match.append(1 if req >= understanding[i] else 0)
            else:
                match.append(1 if req <= understanding[i] else 0)
        if sum(match) < len(understanding):
            Middleware.handle('Leverage Failed', interaction, emoting)
            return
        psychotic = target.character.disorders.find('Psychotic')
        pivot_type = PsychePivot.TYPES['explored']
        understood_time = item.action_time * sum(understanding)
        pivot = PsychePivot(
            target_from=interaction.character,
            target_to=interaction.part,
            when=RpgTick.CURRENT,
            related=item,
            type=pivot_type,
            duration=item.action_time,
            total=understood_time * pivot_type.ratio * psychotic.total,
        )
        for func in item.functions:
            disorder = target.character.disorders.find(
                func, auto_create=False)
            phobia = target.character.phobias.find(func, auto_create=False)
            if disorder:
                disorder.pivots.append(pivot)
            if phobia:
                phobia.pivots.append(pivot)
        found = [
            l for l in target.character.leveraged if l.name == item.name]
        if found:
            leverage = found[0]
        else:
            leverage = PsycheLeverage(item.name, item)
        # Enforcement of a leverage is the number of pivots.
        # Awareness is from the pivots with a target_from.
        leverage.pivots.append(pivot)
        target.character.leveraged.append(leverage)
        Middleware.handle('Leverage Success', leverage)

    @staticmethod
    def interaction_search(action, interaction):
        """
        Action for the character an update to handle search results.

        Depending on the type of search and the search results returned
        give the character a notification of the find of another character,
        for specific searches like 'Soul Divining' the search will
        automatically be stored against the character searching. Management
        of search results is a task outside of this framework as required
        interactions is a specific task to game, expected interactions for
        any search results stored is add and remove.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        if interaction.action == 'Soul Divining' and interaction.part:
            if type(interaction.part) is not list:
                interaction.part = [interaction.part]
            interaction.character.character.souls += interaction.part
        Middleware.handle(interaction.action, interaction.part, interaction)

    @staticmethod
    def interaction_trade(action, interaction):
        """
        Handle a response to a trade request.

        All items for sale are represented in the TradeSlip from
        `interaction.part` where the model defines the sale relationship
        between the two characters. There is a demand for a value given
        which if met is accepted by the seller although with some haggling
        and potentially additional leveraging another TradeSlip can be
        requested with updated prices.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        if bool(
            type(interaction.part) is not TradeSlip and
            type(interaction.item) is not PlayerCharacter
        ):
            return
        slip = interaction.part
        character = interaction.item
        valid = CharacterHandler.licenses_regional(interaction.character)
        temp_list = [l.access for l in valid]
        licensed_access = []
        for a in temp_list:
            licensed_access += a
        unlicenced = [
            i for i in slip.items
            if (
                i.type.name not in rpg_const.LICENSES_TRADE and
                i.type.name not in licensed_access
            )
        ]
        if unlicenced:
            business = interaction.character.abilities.find('Bargain')
            capable = AbilityHandler.as_ability(business)
            deviant = PsycheHandler.deviancy_multiplier(
                interaction.character)
            for item in unlicenced:
                valuation = slip.valuations[slip.items.index(item)]
                sale = valuation['sale_leveraged']
                valuation['sale_leveraged'] = sale + deviant
                expected = valuation['demand']
                if not expected:
                    expected = search_effect(item.name).rrp
                    expected += capable.amount_draw + item.superstition
                valuation['demand'] = expected + (expected * deviant)
                valuation.update({'unlicenced': True, })
        account = MediumChannel.trade_account(character, slip)
        if slip not in account.trades:
            account.trades.append(slip)
        Middleware.handle('Trade Slip', slip, interaction)

    @staticmethod
    def interaction_bid(action, interaction):
        """
        Handle a response to a trade bid.

        Complete a bid request from another PlayerCharacter character where
        all remaining debit supplied to a TradeSlip as change will be
        returned to the PlayerCharacter requesting the bid and all items
        selected for purchase will be transferee. Any items unable to be
        transferred into the characters containers will be dropped into the
        world with the characters vector information.

        :param action: str, the action of this interaction method.
        :param interaction: Interaction, the details being managed.
        """
        if bool(
            type(interaction.part) is not TradeSlip and
            type(interaction.item) is not PlayerCharacter
        ):
            return
        slip = interaction.part
        character = interaction.item
        account = MediumChannel.trade_account(character, slip)
        if slip.debit.quantity:
            account.debit.add(slip.debit.remove_first())
        while slip.receipt.quantity:
            item = slip.receipt.remove_first()
            CharacterHandler.personalise(item, character)
            container = character.body.find_contains(item)
            if container:
                container.add(item)
            else:
                item = ObjectHandler.externalise_model(item, character.body)
                Middleware.handle('Bid Transfer External', item, character)
        # TODO: Feedback to characters on a successful trade.

    @staticmethod
    def interaction_incoming(interaction):
        """
        Character deals with the action from the universe.
        And visa versa ...
        ObjectItem deals with the action from the universe and characters.

        Read details specific to the `action` supplied from the interaction
        object through this function, placing all documentation for each type
        of incoming interaction at the topf of this method would read like a
        novel.

        :param interaction: Interaction detailing the interaction happening.
        """
        if type(interaction.action) is str:
            if '|' in interaction.action:
                action = interaction.action.split('|')[0]
            else:
                action = interaction.action
        else:
            action = list(interaction.action)
        if action not in ObjectHandler.BUILTIN_ACTIONS:
            return
        # TODO: Handle feedback to the originator PlayerCharacter afterwards.
        Middleware.handle('{} Pre'.format(action), interaction)
        if action in rpg_const.SEARCH_ACTIONS:
            ObjectHandler.interaction_search(action, interaction)
        else:
            action_name = action.lower().replace(' ', '_')
            method_name = 'interaction_{}'.format(action_name)
            if method_name == 'interaction_incoming':
                return
            if hasattr(ObjectHandler, method_name):
                getattr(ObjectHandler, method_name)(action, interaction)
            else:
                Middleware.handle('Uknown Interaction', action, interaction)
        Middleware.handle('{} Post'.format(action), interaction)

    @staticmethod
    def contact(character, item, body_part=None):
        """
        Connect a free object from the world with the character to have forces
        applied in response to actions in the world.

        :param character: PlayerCharacter object in the world.
        :param item: ObjectItem in the world interacting with character.
        :param body_part: BodyPart The part of a character being contacted.
        """
        interaction = Interaction(character, body_part, item, item.action)
        ObjectHandler.interaction_incoming(interaction)


class ObjectItem(RpgTick):
    """
    Interact with objects within the game.

    Inventory items are not wrapped by this class as that information is
    just a model of properties for an object, this class defines mechanics
    to handle interactions within the world around it.

    Example usage:
    item = ObjectItem('Armoured Vest')

    Where the string 'Armoured Vest' would have to be a known effect in the
    games data loaded before any character generation.

    To extend this class and apply functionality for item specifics for
    functionality `self.act_enabled` will have to be appended to with the
    registered actions able to be handled by the mixin.
    """
    act_enabled = None
    item_model = None
    vector = None
    interactions = None
    interaction_last = 0
    interaction_current = 0
    mode = None
    user_tracking = None
    meta_ability = None

    @property
    def quantity(self):
        return self.item_model.quantity

    @property
    def weight(self):
        return self.item_model.weight

    @property
    def volume(self):
        return self.item_model.volume

    @property
    def weight_total(self):
        return self.item_model.weight_total

    @property
    def volume_total(self):
        return self.item_model.volume_total

    @property
    def name(self):
        return self.item_model.name

    @property
    def type(self):
        return self.item_model.type

    @property
    def group(self):
        return self.item_model.group

    @property
    def actions(self):
        return self.item_model.actions

    @property
    def is_container(self):
        return bool(self.item_model.contains)

    def measure(self):
        return self.item_model.measure()

    def inspect(self, prefix='', show_all=False):
        return self.item_model.inspect(prefix=prefix, show_all=show_all)

    def __action__builtin__(self, action, tracker):
        """Built in DEMAND of a part of this object."""
        targets = self.item_model.find_action(action)
        tracker = self.user_tracking[tracker]
        action = action.lower().replace(' ', '_')
        action_name = '__action__{}'.format(action)
        if hasattr(self, action_name):
            return getattr(self, action_name)(action, tracker, targets)
        else:
            Middleware.handle(
                'Uknown Action', action_name, action, tracker, targets)
        return []

    def __function__builtin__(self, target, interaction):
        """Built in SUPPLY of parts from this object."""
        rtn = False
        tracker = self.user_tracking[interaction.tracker]
        action = interaction.action[0].lower().replace(' ', '_')
        function_name = '__function__{}'.format(action)
        if hasattr(self, function_name):
            rtn = getattr(self, function_name)(target, interaction, tracker)
        else:
            Middleware.handle(
                'Uknown Function', function_name, target, interaction, tracker)
        # TODO: Post MVP. Generate spread affects defined.
        return rtn

    def _action_parser(self, actor, tracker):
        """
        Manage internal action handling with __action__builtin__ actions

        Parse functions to do actions
        """
        actions = actor.actions or []
        interaction_list = []
        if type(actions) is str:
            actions = [actions]
        for act in actions:
            builtin_list = self.__action__builtin__(act, tracker)
            Middleware.handle('ObjectItem Action', self, act, tracker)
            if builtin_list:
                interaction_list += builtin_list
            elif act not in self.act_enabled:
                interaction_list.append(Interaction(None, None, None, (act, )))
        for interact in interaction_list:
            interact.tracker = tracker
            self.user_tracking[tracker]['count'] += 1
        self.interactions += interaction_list

    def function(self, interaction):
        """
        Manage the function of this object.

        Parse actions to do functions.
        """
        if rpg_const.TURN_BASED:
            interaction.action_frames -= 1
        else:
            interaction.action_frames -= RpgTick.DIFF
        remove_ok = True if interaction.action_frames <= 0 else False
        # Find the parts supplying the demands of interaction.action
        func_targets = self.item_model.find_functions(*interaction.action)
        for f_target in func_targets:
            # Perform the supply from the demands of this object.
            self.__function__builtin__(f_target, interaction)
            Middleware.handle(
                'ObjectItem Function', self, f_target, interaction)
            # Stack the demands of this object for another game tick.
            self._action_parser(f_target, interaction.tracker)
        if remove_ok:
            self.interactions = [
                i for i in self.interactions if i is not interaction]
            self.user_tracking[interaction.tracker]['count'] -= 1

    def tick(self):
        """Manage steps required on game FPS of this object."""
        if len(self.interactions):
            for interact in self.interactions:
                if interact.character != self:
                    if issubclass(interact.character.__class__, ObjectItem):
                        ObjectHandler.interaction_incoming(interact)
                    else:
                        self.function(interact)
            return
        feedback = []
        for key in self.user_tracking.keys():
            if not self.user_tracking[key]['count']:
                feedback.append(key)
        if feedback:
            for key in feedback:
                interaction = self.user_tracking.pop(key)['interaction']
                self.interact_feedback(interaction)
                interaction.character.interact_feedback(interaction)

    def stop_interaction(self, interaction):
        """
        Stop any ongoing interactions with this object.
        Update the character with the relevant time spent in performing
        this interaction.
        """
        pass

    def interact_feedback(self, interaction):
        """
        Take the information from the interaction just performed and apply
        values expected of change on this item as a result from the
        interaction.

        :param interaction: The interaction performed on this item.
        :return: Interaction
        """
        if type(self.item_model.fatigue) is not int:
            self.item_model.fatigue = int(self.item_model.fatigue)
        self.item_model.fatigue += interaction.timing
        return interaction

    def interact(self, interaction):
        """
        Path to the actioning of the object and connect to the root of the body.

        :param interaction: The interaction happening on this item.
        :return: Interaction
        """
        requirements = (
            self.item_model.requires
            if type(self.item_model.requires) is list else
            [self.item_model.requires])
        req_met = [1 for i in requirements if i in interaction.part.actions]
        if not interaction or not sum(req_met):
            raise Exception('Required interaction not available.')
        path = self.item_model.find_functions(*interaction.action)
        if not path:
            raise Exception(
                'Action {} is not available from this item: {}.'.format(
                    interaction.action,
                    self,
                ))
        # Define the time of this object to be interacted with.
        time = float(self.item_model.action_time)
        control_timing = time
        for i in path:
            avail = i.function_ratio(*interaction.action)
            if type(i.circulation) is str:
                i.circulation = float(i.circulation)
            # This timing builds upon itself each connection
            control_timing += control_timing + time
            time += time * ((1 - i.circulation) + (1 - avail))
        interaction.timing = time
        interaction.control_timing = control_timing
        interaction.tracker = hash_generate()
        self.user_tracking.update({interaction.tracker: {
            'count': 0,
            'started': RpgTick.CURRENT,
            'interaction': interaction,
        }})
        next_action = Interaction(self, None, path[-1:][0], interaction.action)
        next_action.tracker = interaction.tracker
        self.user_tracking[interaction.tracker]['count'] += 1
        self.interactions.append(next_action)
        self.function(next_action)
        self.interaction_last = RpgTick.CURRENT
        return interaction

    def __init__(self, search=None, save=None, *args, **kwargs):
        if not save:
            self.item_model = build_object_item(search) if search else None
        else:
            if type(save) is str:
                self.item_model = BodyPart(save_id=save)
                Middleware.handle('ObjectItem Load', self)
            elif type(save) is BodyPart:
                self.item_model = save
            else:
                return
        if self.item_model:
            for option in self.item_model.affect:
                if option.name == 'Default':
                    self.mode = option.ratio
        self.vector = None
        self.interactions = []
        self.user_tracking = {}
        self.act_enabled = []
        super().__init__(*args, **kwargs)

    def __str__(self):
        return '<ObjectItem "{}", container: {}>'.format(
            self.name, self.is_container)


class ObjectProjects:
    """
    Project a projectile from a part of the item with the corresponding action
    and functionality, there is only 1 item able to projected at one time.

    Actions and Functions required for operation: 'Project' and 'Accuracy'.
    """

    class Meta:
        abstract = True

    def __action__project(self, action, tracker, targets):
        """
        Manage the available rate of projection from this object.
        """
        rtn = []
        for target in targets:
            if 'project_count' not in tracker.keys():
                tracker['project_count'] = 0
            if len(target.contains.items) < 1:
                continue
            new_interaction = Interaction(
                None, target, ObjectItem(), (action, ))
            # Check for timings already active on object.
            last_actioned = int(
                tracker['projected'] if 'projected' in tracker.keys() else 0
            )
            # Check the mode timings for this type of action.
            release_time = sum([
                int(s.ratio) for s in target.affect
                if self.mode and self.mode in s.name
            ])
            # Check for turn based system being active
            if rpg_const.TURN_BASED:
                release_time = release_time / rpg_const.TURN_RATE_MIN
                if release_time < 1:
                    release_time = 1
            release_time += last_actioned
            active = [i for i in self.interactions if action in i.action]
            action_fail = not target.contains.items
            if self.mode == 'Single' and tracker['project_count'] >= 1:
                action_fail = True
            elif self.mode == 'Triple' and tracker['project_count'] >= 3:
                action_fail = True
            if action_fail or active or release_time > RpgTick.CURRENT:
                continue
            tracker['project_count'] += 1
            tracker['projecting'] = last_actioned + release_time
            new_interaction.action_frames = last_actioned + release_time
            rtn.append(new_interaction)
        return rtn

    def __function__accuracy(self, target, interaction, tracker):
        """
        Stat based accuracy determined from the characters use and the
        weapons provided affects.
        """
        rtn = True
        tracker['Accuracy'] = interaction
        return rtn

    def __function__project(self, target, interaction, tracker):
        """
        Provide a series of vectors to a child object being projected from
        this ObjectItem to allow external libraries to handle the physics
        and Game World simulations.
        """
        rtn = False
        expected_actioned = int(
            tracker['projecting']
            if 'projecting' in tracker.keys()
            else 0
        )
        if not interaction.part or expected_actioned > RpgTick.CURRENT:
            return rtn
        bullets = [
            b for b in target.contains.items if b.group.name == 'Bullet']
        if not bullets:
            return rtn
        rtn = True
        interaction.action_frames = 0
        item = interaction.item
        item.item_model = target.contains.remove(bullets[0])
        Middleware.handle('Position Vector', self)
        item.vector = duplicate_object(self.vector, default=BodyVector())
        item.meta_ability = tracker['interaction']
        accuracy = (
            AbilityHandler.distance_ratio(item.meta_ability)
            if not item.meta_ability.distance_ratio else
            item.meta_ability.distance_ratio
        )
        ratio = 1
        if interaction.part.group.name in ['Telekinesis']:
            psy_act = AbilityHandler.as_ability(
                item.meta_ability.character.abilities.find(
                    interaction.part.group.name)
            )
            ratio = psy_act.accustomed
        for affect in item.item_model.affect:
            if affect.name == 'Velocity 0':
                item.vector.speed = float(affect.ratio) * ratio
        tracker['projected'] = RpgTick.CURRENT
        # TODO: Process accuracy through a vector modification utility.
        accuracy_mods = self.item_model.find_affect('Accuracy')
        accuracy = item.item_model.find_affect('Accuracy')
        if accuracy:
            accuracy_mods += accuracy[1:]
            for mod in accuracy:
                item.item_model.affect.pop(mod)
            accuracy = accuracy[0]
        else:
            accuracy = StatType(name='Accuracy', ratio=1)
        radiations = item.item_model.find_affect('Radiation')
        radiation_mods = []
        for radiation in radiations:
            mods = self.item_model.find_affect(radiation.name)
            for mod in mods:
                radiation_mods.append(mod)
                radiation.ratio += mod.value
        for mod in accuracy_mods:
            accuracy.ratio += mod.ratio
        item.item_model.affect.append(accuracy)
        Middleware.handle('Project Accuracy', item, accuracy)
        # TODO: Projected item has equal and opposite reaction to item: recoil.
        for key, value in enumerate(rpg_const.DAMAGE_MODIFIERS):
            if value.name == 'Accuracy':
                pass

    def __init__(self, search=None, save=None, *args, **kwargs):
        super().__init__(search=search, save=save, *args, **kwargs)
        self.act_enabled.append('Project')


class ObjectFeeds:
    """
    mixin to manage the feed functionality of ObjectItem items to enable a
    feeding of items contained from one part into another container.

    Actions and Functions required for operation: 'Feed' and 'Recieve'.
    """

    class Meta:
        abstract = True

    def __action__feed(self, action, tracker, targets):
        """
        Take an amount from the identified targets' containers and supply
        the contents to an interaction for inclusion to another container.
        """
        rtn = []
        if [i for i in self.interactions if action in i.action]:
            return rtn
        func_targets = self.item_model.find_functions(action)
        distribution = len(func_targets)
        count = sum([t.contains.quantity_remaining() for t in func_targets])
        if not count:
            return rtn
        for target in targets:
            if len(target.contains.items) < 1:
                continue
            items = ObjectHandler.pattern_selection(target, select=count)
            for item in items:
                rtn.append(
                    Interaction(None, target, item, (action, distribution)))
        return rtn

    def __function__feed(self, target, interaction, tracker):
        """
        Add the allotted amount to the target part, for multiple actions
        required the ceiling integer is removed from the spread.
        """
        rtn = True
        if not interaction.part:
            return rtn
        amount = ceil(interaction.action[1])
        if interaction.item.quantity <= amount:
            item = interaction.item
        else:
            item = duplicate_object(interaction.item)
            item.quantity = amount
            interaction.item -= amount
        try:
            target.contains.add(item)
        except Exception:
            interaction.part.contains.add(item)
        else:
            pass
        return rtn

    def __init__(self, search=None, save=None, *args, **kwargs):
        super().__init__(search=search, save=save, *args, **kwargs)
        self.act_enabled.append('Feed')


class GunItem(ObjectItem, ObjectProjects, ObjectFeeds):
    """
    ObjectItem able to manage the functionality of both a feeding system for
    cartridges and for projecting projectiles.
    """
    pass


rpg_const.REGISTERED_CLASSES.append('ObjectItem')
rpg_const.REGISTERED_CLASSES.append('GunItem')


def create_object(id):
    """
    Create an object representing the data and statistics of stored information
    by checking what functionality is required per type of skill required of
    the ObjectItem.
    """
    if not id:
        return None
    item = build_object_item(id)
    package = None
    clazz = None
    for skill in rpg_const.CLASSES.stats:
        if skill.name == item.type.name:
            package = skill.package
            clazz = skill.class_name
            break
    if not clazz or not package:
        raise Exception('Object not buildable for skillset: {}.'.format(id))
    clazz = getattr(importlib.import_module(package), clazz)
    if not clazz:
        raise Exception('Failed to find functional class.')
    return clazz(search=id, save=item)


class MediumChannel(ObjectItem):
    """
    Communication channel through a medium type.

    Weightings are a user defined modification of mood infliction towards this
    conversation.
    """
    ACTION_TYPE = 'Medium'

    non_targeted = rpg_const.SEARCH_ACTIONS
    weightings = None

    @staticmethod
    def trade_account(target, slip=None):
        """
        Find the account being traded with for a specific target.

        :param target: PlayerCharacter identifying the trade account of.
        :param slip: TradeSlip, defaults None, current slip being transacted.
        :return: CharacterAccount
        """
        account = target.character.body.first_account()
        if not slip:
            return account
        if type(slip) is not TradeSlip:
            return account
        if slip not in account.trades.keys():
            account = [
                a for a in target.character.body.accounts
                if slip in a.trade.keys()]
            if not account:
                Middleware.handle('Account TradeSlip Unknown', slip)
                return
            account = account[0]
        return account

    @staticmethod
    def trade_goods(target):
        """
        Define a list of goods for trade from the seleted target.

        :param target: PlayerCharacter whom is a valid seller.
        :return: list
        """
        if (
                type(target) is not PlayerCharacter or
                not target.character.accounts
        ):
            raise Exception(
                'Seller "{}" is not a valid sentient being.'.format(target)
            )
        contains = [
            part.contains.items
            for part in target.character.body.whole.list_contains()
            if part.contains.quantity > 0
        ]
        items = []
        for contained in contains:
            items += contained
        return items

    @staticmethod
    def trade_leverage(known_leverage, requester):
        """
        Handler to define the leverage being applied to a trade request.

        :param known_leverage: dict, known leverage of the seller.
        :param requester: PlayerCharacter, the potential buyer.
        :return: float, float

        The return is two float values:
        1. Sales modifier to change the goods available to be sold.
        2. Demand modifier to change the value of the goods sold.

        HACK: Point of note about the `aware` and `enforced` variables for a
        piece of leverage and the use of a paired list in absence of a class
        defining the distinct values; This is just a hack and expected to be
        corrected for production post MVP.
        """
        if (
            type(requester) is not PlayerCharacter or
            not requester.character.accounts
        ):
            raise Exception(
                'Buyer "{}" is not a valid sentient being.'.format(requester)
            )
        mod_sales = 0
        mod_demand = 0
        for leverage in known_leverage:
            aware = leverage.aware_from(requester)
            rate = float(
                ease_mult(aware, ceil(aware)) *
                ease_mult_cap(leverage.enforced, aware)
            )
            mod_sales += sum([
                a.total for a in leverage.related.affect
                if a.name == 'Sale'
            ]) * rate
            mod_demand += sum([
                a.total for a in leverage.related.affect
                if a.name == 'Demand'
            ]) * rate
        return mod_sales, mod_demand

    @staticmethod
    def random_rate(ability=None):
        value = random() * 1000000000 % rpg_const.SEARCH_RATE
        return value + (ability.accustomed if ability else 0)

    @staticmethod
    def _conversation_dynamics(dynamics, target, known_dynamics):
        """
        Provide a list of connections of a conversation which are identified
        as dynamic identifiers for items in the world and containers in
        reference to those involved in the conversation.

        Single reference: '#Food Fridge#' is an ID to the world item with the
                                          name of 'Food Fridge', and will be
                                          referred to throughout the
                                          conversation using that identifier.

        Dual reference: '#Food:Fowl#' identifies either a name or a group of an
                                      object reference in a container of
                                      another referred object with the
                                      requirement of possessing the affect post
                                      the colon.

        :param dynamics: list of string identifiers.
        :param target: PlayerCharacter the conversation is directed towards.
        :param known_dynamics: dict of known effects required of conversation.
        :return: dict of know effects required of conversation.
        """
        contained = []
        rtn = {}
        for dynamic in dynamics:
            if dynamic in rpg_const.CACHE.keys():
                rtn[dynamic] = rpg_const.CACHE[dynamic]
                continue
            value = dynamic[1:-1]
            if ':' in value:
                value = value.split(':')
            else:
                value = [value]
            if len(value) == 1:
                # Process all known active objects for an ID match
                # TODO: Post MVP. DB reference for in world items ID.
                effect = [e for e in RpgTick.KNOWN if e.name == value[0]]
                effect = effect[0] if effect else None
                if not effect:
                    effect = [e for e in dynamics if e.name == value[0]]
                    effect = effect[0] if effect else None
            else:
                # Identify items contained by known dynamics (not str)
                if not contained:
                    known_containers = target.list_contains(all_parts=True) + [
                        known_dynamics[k].list_contains(all_parts=True)
                        for k in known_dynamics.keys()
                    ]
                    for container in known_containers:
                        contained += container.items
                searched = [
                    s for s in contained
                    if value[1] in [a.name for a in s.affect]
                ]
                effect = [
                    e for e in searched if (
                        (e.name == value[0] or e.group.name == value[0]) and
                        e not in known_dynamics.values()
                    )
                ]
                if len(effect) > 1:
                    effect = choice(effect)
                else:
                    effect = effect[0] if effect else None
            rtn[dynamic] = effect
            # TODO: Ensure expiry of conversation cache effects are maintained.
            rpg_const.CACHE[dynamic] = effect
        return rtn

    def __action__builtin__(self, action, tracker):
        """
        Built in DEMAND of a part of this object.

        Change in operation from inherited format, this method is called
        globally before targets are selected for direct interaction.
        """
        pass

    def __function__bind_soul(self, source, tracker, target, interaction):
        """
        Target soul is expected to be bound to an item

        Imbuing a soul into an item binds a soul to a physical object,
        sentient or consciousness of the soul factors only for certain types
        or make ups of soul to provide an ability at a minimum: Imbibe.
        A soul expectant to be conscious has an expectation of
        conversational leverages to be upheld where common goals and
        activities are enforced and reinforced cyclically, beyond the bond
        to the object the will of both souls working with free will by the
        actions observed. Exampling war: A murderous rampaging soul expects
        to be placed on a weapon to kill instead of a healing vessel.

        For a construct to be bound to a soul it is the souls job to manage
        its own body and power the construct to be present in the physical
        world, otherwise a rate of energy will be consumed equal to mass of
        the construct and the bound souls energy indicator. Noting that a
        construct is only available in the physical world if there is energy
        available within it's container, upon Impact energy is consumed to
        break velocity of impacts.
        """
        pass

    def __function__imbue_select(self, source, tracker, target, interaction):
        """
        Psychically communicate with an Imbue'ing object and select the type
        of affect to imbue onto another object.
        """
        pass

    def __function__communication(self, source, tracker, target, interaction):
        """
        Converse with a target or group

        Conversation is had through multiple channels and mediums but always
        relies on the two way transfer of information, defining how a
        character acts within a medium is pertinent to the expected
        reactions from others in conversation and potential actions
        afterwards.
        """
        known = {}
        index = 0
        item = source.item
        description = item.description
        descript_dynamics = []
        marker = rpg_const.CONVERSATION_DYNAMIC_MARKER
        while description.index(marker, index) > -1:
            index = description.index(marker, index) + 1
            match = description.index(marker, index)
            if match:
                descript_dynamics.append(
                    '{}{}{}'.format(
                        marker, description[index:match], marker)
                )
                index = match + 1
        if type(source.item) is list:
            item = source.item[0]
        index = -1
        while index < rpg_const.CONVERSATION_DYNAMIC_LIMIT:
            index += 1
            dynamics = [
                c for c in item.connections + descript_dynamics
                if type(c) is str and c not in known.keys()
            ]
            known.update(
                MediumChannel._conversation_dynamics(
                    dynamics, target, known)
            )
        targeted_interaction = duplicate_object(source)
        dynamics = [c for c in source.item.connections]
        for dynamic in dynamics:
            targeted_interaction.item.description = description.replace(
                dynamic, known[dynamic].name)
        targeted_interaction.character = source.character
        targeted_interaction.targets = None
        targeted_interaction.tracker = interaction.tracker
        targeted_interaction.medium = self
        ObjectHandler.interaction_incoming(targeted_interaction)

    def __function__search(self, source, tracker, target, interaction):
        """
        Perform a search for characters within this medium.

        Searching functions are targetless and will not have the `target`
        argument passed, it is a requirement only from the character
        performing the action to interact with.
        """
        character = source.character.character
        openess = character.abilities.find('Openess')
        capable = AbilityHandler.as_ability(openess)
        rate = MediumChannel.random_rate(capable)
        search_success = rate > rpg_const.SEARCH_RATE - 1
        found = []
        if search_success:
            count = -1
            rate = int(rate)
            # TODO: Pre-select list restricted by distance or ear shot.
            # in_distance = []
            while count < rate:
                found.append(choice(self.item_model.connections))
        if (
                (self.item_model.name == 'Universe' and
                 interaction.action == 'Soul Divining') or
                (self.item_model.name == 'Internet' and
                 interaction.action == 'Net Search')
        ):
            """
            Perform a secondary check to generate a bunch of souls of
            varying strengths determined from a spread, the number of souls
            generated can remain low at 1 or 2 each time as a 'search' from
            any medium has a delayed processing to maintain validity within
            the game environment (not chew up too much resources).
            """
            divining = character.abilities.find(interaction.action)
            capable = AbilityHandler.as_ability(divining)
            rate = MediumChannel.random_rate(capable)
            if rate > rpg_const.SEARCH_RATE - 1:
                count = -1
                rate = int(rate)
                while count < rate:
                    # TODO: have the soul generate with a specific level.
                    soul = PlayerCharacter()
                    self.item_model.connections.append(soul)
        if not search_success:
            frames = rpg_const.FRAME_RATE_MIN * rpg_const.SEARCH_RATE
            interaction.action_frames = frames
            self.interactions.append(interaction)
        targeted_interaction = Interaction(
            character, found, None, source.action)
        targeted_interaction.tracker = interaction.tracker
        targeted_interaction.medium = self
        ObjectHandler.interaction_incoming(targeted_interaction)

    def __function__leverage(self, source, tracker, target, interaction):
        """
        Psychologically manipulate a character to change their attitude.

        For a piece of leverage to manage the target characters opinion
        about a goal or agreement to a disorder the target needs to be made
        aware and have the leverage enforced by the agressing character.
        With this action through a medium others in close proximity or
        directly listening to the location have a chance to over hear the
        conversation and be made aware of the situation themselves.
        """
        targeted_interaction = duplicate_object(source)
        targeted_interaction.character = source.character
        targeted_interaction.targets = None
        targeted_interaction.tracker = interaction.tracker
        targeted_interaction.medium = self
        ObjectHandler.interaction_incoming(targeted_interaction)

    def __function__trade(self, source, tracker, target, interaction):
        """
        Request a list of trade items from another PlayerCharacter.

        All items for trade are supplied as a response if the other
        PlayerCharacter is accepts the trade taking place with the
        requesting PlayerCharacter, this is a personal vetting of trust
        between each other and adjusts the overall viability of items for
        sale.

        Options required to consider:
        Price Paid = how much the other person paid for the item
        Lowest = sellers lowest value of the item
        Leveraged = sellers demand post leverage considerations
        Buy? = buyer can buy the item

        Response expects to include for each item:
        Sale? = likelihood of the other character selling an item
        Leveraged Sale? = saleability post leveraged considerations
        Demand = sellers demand of the item
        Haggling Weighting = ratio the requester can take into consideration
                             when bidding for the items sale.

        Not expected to take into consideration as is the variable from the
        traded value of the item.
        Willing = buyers willing value of the item
        This could likely be turned into a budget to browse through.
        """
        business = target.character.abilities.find('Bargain')
        capable = AbilityHandler.as_ability(business)
        valuations = []
        response = []
        items = MediumChannel.trade_goods(target)
        known_leverage = [
            leverage
            for leverage in target.character.leveraged
            for pivot in leverage.pivots
            if pivot.target_from == source.character
        ]
        mod_sales, mod_demand = MediumChannel.trade_leverage(
            known_leverage, source.character
        )
        if mod_sales < 0:
            Middleware.handle('Trade Denied', target, source)
            return
        for item in items:
            expected = item.price
            if not expected:
                expected = search_effect(item.name).rrp
                expected += capable.amount_draw + item.superstition
                item.price = expected
            for_sale = int(item.for_sale) - item.superstition
            if for_sale < 0:
                for_sale = 0
            if item.type.name not in rpg_const.LICENSES_TRADE:
                for_sale = 0
            if rpg_const.PERSONALISATION_LEVEL > 0:
                item = CharacterHandler.personalise(item, target)
            response.append(item)
            valuations.append({
                'sale': for_sale,
                'sale_leveraged': for_sale * mod_sales,
                'demand': expected * mod_demand,
            })
        slip = TradeSlip(response, valuations)
        account = MediumChannel.trade_account(target)
        account.trades.update({slip: items})
        targeted_interaction = Interaction(
            target, slip, source.character, source.action)
        targeted_interaction.tracker = interaction.tracker
        targeted_interaction.medium = self
        ObjectHandler.interaction_incoming(targeted_interaction)

    def __function__bid(self, source, tracker, target, interaction):
        """
        Place a bid on an item from another PlayerCharacter.

        By placing a bid on an item the seller must supply the funds along
        with the bid to have it rejected directly and notify the buyers
        position as rejected, otherwise remove the funds from the account
        and instantly give the item to the buyer. Items unable to be carried
        by the buyer will manifest outside of models and appear as an
        ObjectItem, this means the buying PlayerCharacter will have dropped
        the item in front of them.

        By default the TradeSlip is passed via `interaction.part`.
        """
        if type(source.part) is not TradeSlip:
            return
        slip = source.part
        mod_sales, mod_demand = MediumChannel.trade_leverage(
            target.character.leveraged, source.character
        )
        if mod_sales < 0:
            Middleware.handle('Bid Denied', target, source)
            return
        account = MediumChannel.trade_account(target, slip)
        if not account or slip.selected:
            return
        sub_total = 0
        volume = 0
        for item in slip.selected:
            index = slip.items.index(item)
            volume += item.volume_total
            valuation = slip.valuations[index]
            sub_total += valuation['demand']
        if slip.debit.quantity < sub_total:
            Middleware.handle('Bid Insufficient', slip)
            return
        if slip.receipt.max_volume < volume:
            slip.receipt.max_volume = volume
        trade_items = account.trades[slip]
        for item in slip.selected:
            index = slip.items.index(item)
            slip.receipt.add(trade_items[index])
        account.debit.add(slip.debit.remove(quantity=sub_total))
        targeted_interaction = Interaction(
            target, slip, source.character, source.action)
        targeted_interaction.tracker = interaction.tracker
        targeted_interaction.medium = self
        ObjectHandler.interaction_incoming(targeted_interaction)

    def __function__builtin__(self, target, interaction):
        """
        Built in SUPPLY of parts from this object.

        Change in operation from inherited format, on each target found in
        self.connections this method will be called to manage the
        personalisation for each interaction.
        """
        tracker = self.user_tracking[interaction.tracker]
        source = tracker['interaction']
        if type(target) is not PlayerCharacter:
            raise Exception(
                'Valid sentient being required, given: "{}".'.format(target)
            )
        if interaction.action in rpg_const.SEARCH_ACTIONS:
            self.__function__search(source, tracker, target, interaction)
        action_name = interaction.action.lower().replace(' ', '_')
        function_name = '__function__{}'.format(action_name)
        if hasattr(self, function_name):
            getattr(self, function_name)(source, tracker, target, interaction)
        else:
            Middleware.handle(
                'Function Unknown', function_name, source, tracker, target,
                interaction
            )

    def function(self, interaction):
        """
        Handle connections between all PlayerCharacters in this channel, targets
        within the Interaction is required as a PlayerCharacter cannot shout
        to everyone else unless they are psychic, and that would take a huge
        amount of time to process for a AAA game.

        :param interaction: The interaction happening in this channel.
        :return: Interaction used for the this method.
        """
        interaction.action_frames -= 1
        if interaction.action_frames > 0:
            return interaction
        if not interaction.character.character.conscious:
            return
        if interaction.character not in self.weightings.keys():
            self.weightings.update({interaction.character: [0] * 6})
        if interaction.action in self.non_targeted:
            self.__function__builtin__(None, interaction)
            Middleware.handle('Medium Function', self, None, interaction)
        else:
            if type(interaction.targets) is list:
                targets = [
                    t for t in self.item_model.connections
                    if t in interaction.targets and t.character.conscious
                ]
            else:
                # TODO: Target validation for ear shot and distance required.
                targets = [t for t in self.item_model.connections
                           if t is interaction.part and t.character.conscious]
            for target in targets:
                self.__function__builtin__(target, interaction)
                Middleware.handle('Medium Function', self, target, interaction)
                self.__action__builtin__(target, interaction.tracker)
        self.interactions = [
            i for i in self.interactions if i is not interaction]
        self.user_tracking[interaction.tracker]['count'] -= 1
        return interaction

    def stop_interaction(self, interaction):
        """
        Stop any ongoing interactions with this object.
        Update the character with the relevant time spent in performing
        this interaction.
        """
        found_interactions = [
            i for i in self.interactions
            if (
                i.action == interaction.action and
                i.character is interaction.character
            )
        ]
        for found in found_interactions:
            self.interactions.remove(found)
            interaction = self.user_tracking.pop(found.tracker)['interaction']
            interaction.character.interact_feedback(interaction)

    def interact(self, interaction):
        """
        Path to the actioning of the object and connect to the root of the body.

        :param interaction: The interaction happening on this item.
        :return: Interaction
        """
        interaction = super().interact(interaction)
        if interaction.action in rpg_const.SEARCH_ACTIONS:
            frames = rpg_const.FRAME_RATE_MIN * rpg_const.SEARCH_RATE
            interaction.action_frames = frames
        return interaction

    def __init__(self, search=None, save_id=None, *args, **kwargs):
        super().__init__(search=search, save_id=save_id, *args, **kwargs)
        self.weightings = {'default': [0] * 6}

    def __str__(self):
        return '<MediumChannel "{}", requires: {}>'.format(
            self.name, self.item_model.requires)


class PlayerCharacter(RpgTick):
    """
    Definition of interactions for a character.

    Example usage:
    rpg_const.PLAYER = PlayerCharacter()
    rpg_const.PLAYER.birth(name='Joe swanson')

    This example will provide a bare bones living 20 something year old with
    a core understanding of a history with full stats as defined from the data
    provided.

    Note on updating statistics through this framework for a character the
    method `binding_downn` is used to pass a string which is interpreted as
    the commands to update the PlayerCharacter. A syntax is observed:
    “m [stat type] [stat detail] [integer]”
    An example string the following will add 5 to the skill Pistols:
    “m skills pistols 5”
    Showcasing an updated with a space in teh name:
    “m disorders Parkinsons Disease 5000”
    """
    VECTOR_STILL = BodyVector(speed=('Still', 0), direction=0)

    _hold_binding = None
    _pack = None

    character = None
    npc = None
    vector = None
    vectors_incoming = None
    binding = None
    interactions = None
    feedback_queue = None
    targeting = None
    torso = None
    manipulators = None
    readied = None
    movement = None
    posture = None

    @property
    def level(self):
        return CharacterHandler.evaluate_level(self)

    @property
    def bound(self):
        mod = 0 if self.character.body else -1
        return len(self.character.bound_bodies) + mod

    @property
    def body(self):
        return self.character.body.whole if self.character.body else None

    @property
    def name(self):
        body = self.character.body
        return body.name if body else self.character.name

    @property
    def right_hand(self):
        hand = self.body.find_name('Right Hand', in_children=True)[-1:]
        return hand[0] if hand else None

    @property
    def left_hand(self):
        hand = self.body.find_name('Left Hand', in_children=True)[-1:]
        return hand[0] if hand else None

    """------------------------------------------------
            === Feedback methods ===
    ------------------------------------------------"""

    def allocate(self, group, name, points=1):
        """
        Direct allocation of values to stat.

        :param group: StatGroup name [stats|disciplines|skills].
        :param name: Stat name, case sensitive.
        :param points: int points to allocate.
        """
        if type(group) is str:
            group = group.lower()
            if group not in [
                'stats', 'disciplines', 'skills', 'disorders', 'phobias',
            ]:
                print('Stat group: "{}" is unknown.'.format(group))
                return
            group = getattr(self.character, group)
        if group in ['disorders', 'phobias']:
            pivot = PsychePivot(
                type=PsychePivot.TYPES['analysed'],
                duration=points,
                multiplier=1,
                target_to=self,
            )
            stat = group.find_name(name)
            if not stat:
                return
            stat.psyche.append(pivot)
            return
        group.allocate(name, int(points))

    def _update_indicators(self):
        """Update the indicators to for the max values."""
        for ind in self.character.indicators:
            ind.calc_max()

    def _reset_indicators(self):
        list_ind = ['Energy', 'Concentration', 'Fatigue', 'Health']
        for ind in list_ind:
            ind = self.character.indicator(ind)[0]
            ind.ms = 0
            ind.offset = 0
        self._update_indicators()

    def _indicator_ms_consolidation(self):
        """
        Updates indicators with the correct value, the only one expected to
        need direct updates is teh health indicator where a evaluation of a
        body is required depending on the observability of the body inhabiting.
        """
        energy = 0
        fatigue = 0
        concentration = 0
        for interaction in self.interactions:
            search = interaction.item or interaction.action
            if type(search) in [list, tuple, set, ]:
                search = search[0]
            ability = self.character.abilities.find(search, auto_create=False)
            if not ability:
                continue
            AbilityHandler.ability_definitions(ability, self)
            skill = ability.skill
            stats = []
            if type(skill) is not str:
                stats = skill.stat
                if type(stats) is str:
                    stats = [stats]
                skill = skill.name
            for stat in stats:
                stat = self.character.stats.find(stat)
                for d_stat in stat.draw:
                    if d_stat.name == 'Energy':
                        energy += interaction.energy_ms * d_stat.ratio
                    elif d_stat.name == 'Fatigue':
                        fatigue += interaction.fatigue_ms * d_stat.ratio
                    elif d_stat.name == 'Concentration':
                        concentration += (
                            interaction.concentration_ms * d_stat.ratio)
        self.character.indicator('Energy')[0].ms = energy
        self.character.indicator('Concentration')[0].ms = concentration
        if not self.character.body:
            fatigue_ind = self.character.indicator('Fatigue')[0]
            fatigue_ind.ms = 0
            fatigue_ind.offset = fatigue_ind.max
            health_ind = self.character.indicator('Health')[0]
            health_ind.ms = 0
            health_ind.offset = health_ind.max
            return
        if self.character.body:
            vitals = self.character.body.whole.find_type(
                'Vital', all_parts=True)
            health = sum([int(part.health_ms) for part in vitals])
        self.character.indicator('Fatigue')[0].ms = fatigue
        self.character.indicator('Health')[0].ms = health

    """------------------------------------------------
            === Container management methods ===
    ------------------------------------------------"""

    def add_item(self, item, part=None):
        """Add an item to this characters containers."""
        parts = self.body.find_contains(item)
        if part in parts:
            try:
                part.contains.add(item)
            except Exception:
                part = parts[0]
                part.contains.add(item)
            if rpg_const.PERSONALISATION_LEVEL > 1:
                CharacterHandler.personalise(item, self)
        else:
            None
        return part

    def wearable_item(self, item):
        """Check if the item is wearable and return the parts it is wearable."""
        if item and type(item) is str:
            raise Exception('Str is not a wearable')
        return self.body.find_wears(item)

    def wear_item(self, item, part=None):
        """Find a part or select the given to wear an item on the character."""
        parts = self.body.find_wears(item)
        if part in parts:
            part.wears.add(item)
        else:
            part = parts[0]
            part.wears.add(item)
        if parts and rpg_const.PERSONALISATION_LEVEL > 1:
            CharacterHandler.personalise(item, self)
        return part

    """-----------------------------------------------------
            === Interaction and Reaction methods ===
    -----------------------------------------------------"""

    def _skills_cross_group(self):
        """
        Fetch relative values for skills, this is DB specific and should be
        instantly removed from this class and code all together as the first
        task.

        # HACK: In lieu of a decent DB and MVP this works.
        """
        for s in self.character.skills.stats:
            if not s:
                continue
            value = s.total
            names = s.unknown['Stat']
            if type(names) is str:
                if '|' in names:
                    names = names.split('|')
                else:
                    names = [names]
            n_value = 0
            for n in names:
                stat = self.character.stats.find(n, auto_create=False)
                n_value += stat.total
            n_value /= len(names)
            value *= n_value
            disciplines = s.unknown['Discipline']
            if type(disciplines) is str:
                if '|' in disciplines:
                    disciplines = disciplines.split('|')
                else:
                    disciplines = [disciplines]
            for stat in disciplines:
                stat = self.character.disciplines.find(stat, auto_create=False)
                value *= stat.total
            s.total = value

    def is_interacting_with(self, part):
        """
        Is this character interacting with the given body part and what
        items are being interacted with.

        :param part: BodyPart expected to check for interactions
        :return: list
        """
        rtn = []
        for interaction in self.interactions:
            if interaction.part is part:
                rtn.append(interaction)
        return rtn

    def stop_interaction(self, functioning, part=None):
        """
        Stop the interaction happening from a particular hand.
        This stopping is only effective if the action has not been completed
        through the connection and there is time to intervene withe the action
        from happening. Otherwise 'boom baby'.

        By stopping the interaction early or before a conclusive action is
        performed from an interaction, no feedback is expected other than a
        psychological impact phobia towards a type of thing.

        :param functioning: str, type of interaction to stop happening
        :param part: BodyPart, the part of the body to stop interactions.
        """
        if not part:
            part = self.body.find_function(functioning)
            if not part:
                return
        remove_connections = []
        remove_interactions = []
        for connection in part.connections:
            functions = connection.functions
            if type(connection) is not BodyPart:
                functions = connection.item_model.functions
            if functioning not in functions:
                continue
            remove_connections.append(connection)
            for interaction in self.interactions:
                # Find all the interactions currently happening with this
                # function type.
                if interaction.item is connection:
                    interaction.action_frames = 0
                    remove_interactions.append(interaction)
        for removing in remove_connections:
            part.connections.remove(removing)
        for removing in remove_interactions:
            self.interactions.remove(removing)
            self.interact_feedback(removing)

    def _feedback_delayed(self, interaction):
        """
        Postponed feedback loop into self from completed actions.

        :param interaction: Interaction, action performed regardless of status.
        """
        if interaction not in self.feedback_queue:
            return
        self.feedback_queue.remove(interaction)
        PsycheHandler.interaction_feedback(interaction)

    def interact_feedback(self, interaction):
        """
        Feedback from interactions to update this character.

        :param interaction: Interaction, action performed regardless of status.
        """
        if interaction.character != self:
            return
        required_by = [
            i for i in self.interactions if interaction in i.requires]
        if required_by:
            for req in required_by:
                i = req.requires.index(interaction)
                req.requires = req.requires[:i] + req.requires[i + 1:]
        ability = self.character.abilities.find(interaction.item)
        ObjectHandler.disconnect(interaction.part, interaction.item, ability)
        try:
            i = self.interactions.index(interaction)
        except ValueError:
            i = -1
        amount = AbilityHandler.as_ability(
            self.character.abilities.find('Model Analysis')
        ).amount_draw
        interaction.action_frames = 0
        interaction.feedback_time = (
            rpg_const.FEEDBACK_MILLISECONDS -
            ease_mult(amount, rpg_const.FEEDBACK_MILLISECONDS)
        )
        if interaction.feedback_time < 0:
            interaction.feedback_time = 0
        self.feedback_queue.append(interaction)
        self.interactions = self.interactions[:i] + self.interactions[i + 1:]
        Middleware.handle('Interact Feedback', interaction)

    def _interaction_setup(self, part, item, *args):
        """
        Setup for the interaction between this character and an item.

        :param action: The action expected to happen.
        :param part: Body part expected to interact with the item.
        :param item: Object being acted upon by the body part.
        """
        interaction = Interaction(self, part, item, args)
        ability = self.character.abilities.find(item)
        ObjectHandler.connect(part, item, ability, interaction)
        AbilityHandler.as_ability(ability, interaction)
        result = item.interact(interaction)
        time = float(result.item.item_model.action_time)
        control_timing = time
        root = result.part.find_root()
        avail = root.function_ratio(result.action)
        if type(root.circulation) is str:
            root.circulation = float(root.circulation)
        control_timing += control_timing + time
        time += time * ((1 - root.circulation) + (1 - avail))
        psyche_multiplier = PsycheHandler.ability_psychoses(interaction)
        result.timing += time
        result.control_timing += control_timing
        dist_ratio = (
            AbilityHandler.distance_difficulty(ability, result)
            if not interaction.distance_ratio else
            interaction.distance_ratio
        ) + 1
        result.modifier = psyche_multiplier * (
            result.control_timing - result.timing
        ) * dist_ratio
        if result.timing - result.modifier < 0:
            # Stop interaction because the psyche refuses to comply.
            fail_interaction = item.stop_interaction(result)
            if fail_interaction:
                return
        self.interactions.append(result)
        if result:
            print('{} {}'.format(part.name, args))
        else:
            print('{} can not be done by {}'.format(args, part.name))

    def interact(self, part, *args, object_item=None):
        """
        Interaction between this character and an object.

        If there is already an item in the hand when an interaction is being
        applied to that part, the held item will be acted upon.

        :param part: The part of the character an interaction is taking place.
        :param *args: Action expected to function from ObjectItem.
        :param object_item: The object being interacted with, defined as an
        optional due to 'Hand' objects being able to contain an item are
        accounted for as being the default item being interacted with.
        """
        already_interacting = False
        for interaction in self.interactions:
            if interaction.part == part:
                print('Already performing an action with {}.'.format(part))
                already_interacting = True
        if already_interacting:
            """
            # HACK: short cut for production ready product.
            One body part can perform one action at a time, this is a hard
            rule for the time being until further requirement enables the
            multi use or multiple actions being performed by the same
            body part: Brain performing 2 or more actions at one time.
            """
            return
        interact_contained = ['Hand']
        if part.type.name in interact_contained:
            if not part.contains or part.contains.quantity < 1:
                Middleware.handle('{} Unarmed'.format(part.name), part, *args)
                return
            if not object_item:
                object_item = part.contains.items[0]
            elif object_item not in part.contains.items:
                return
        if rpg_const.PERSONALISATION_LEVEL > 2:
            CharacterHandler.personalise(object_item, self)
        default_action = None
        if hasattr(object_item, 'affects'):
            affect = object_item.affect
        else:
            affect = object_item.item_model.affect
        for option in affect:
            if option.name == 'Default Action':
                default_action = option.ratio
        can_interact = ObjectHandler.can_interact(part, object_item, *args)
        if not can_interact and args and args[0] == default_action:
            return
        else:
            actions = (default_action, )
            actions += args[1:]
            if not ObjectHandler.can_interact(part, object_item, *actions):
                return
            args = actions
        self._interaction_setup(part, object_item, *args)

    def _tick_required_complete(self, complete):
        """
        Remove an interaction from the requires set from other interactions.

        :param complete: Interaction completed to be removed from others.
        """
        for interaction in self.interactions:
            if complete in interaction.requires:
                interaction.requires.remove(complete)

    def tick(self):
        """Game processing tick."""
        self._update_indicators()
        for interaction in self.interactions:
            if not interaction.requires:
                ObjectHandler.interaction_incoming(interaction)
        for interaction in self.feedback_queue:
            interaction.action_frames += RpgTick.DIFF
            if interaction.action_frames > interaction.feedback_time:
                self._tick_required_complete(interaction)
                self._feedback_delayed(interaction)
        self._indicator_ms_consolidation()
        self._binding_count(RpgTick.DIFF)

    """------------------------------------------------
            === Character binding methods ===
    ------------------------------------------------"""

    def _act_psy_charge(self, action, part, target=None, **kwargs):
        """
        Using this characters Psychic ability draw from the Energy indicator
        and charge Construct's connected.

        :param action: str, the action happening.
        ;param part: BodyPart, the part interacting to action.
        :param target: BodyPart, optional target to act with.
        """
        if not part:
            for part in self.manipulators:
                part_targets = part.contains.search(action)
                if part_targets:
                    for target in part_targets:
                        self.interactions.append(
                            Interaction(self, part, target, action))
            return
        if not target:
            return
        if issubclass(target.__class__, ObjectItem):
            target = target.item_model
        if not target.find_functions(action, all_parts=False):
            return
        self.interactions.append(Interaction(self, part, target, action))

    def _act_throw(self, action, part, target=None, **kwargs):
        """
        Project this ObjectItem from the character as all constituent parts
        are attached from the main object and are not thrown individually.

        :param action: str, the action happening.
        ;param part: BodyPart, the part interacting to action.
        :param target: BodyPart, optional target to act with.
        """
        if not part:
            part = self.character.whole.find_name(
                self.character.body.first_hand)
            if not part and self.manipulators:
                part = self.manipulators[0]
        originally_held = part.contains.items
        if not target and part.contains.quantity:
            target = part.contains.items[0]
        if target not in part.contains.items:
            self.act('Holster', self.part)
            self.act('UnHolster', self.part, target=target)
        self.interactions.append(Interaction(self, part, target, action))
        for held in originally_held:
            self.act('UnHolster', self.part, target=target)

    def _act_reload_check_needs(self, item):
        """
        Check an item for requirement of reloading, a stepped return is supplied
        to mimick the volume of the magazine or cartridges available on an item.
        For items which require more than one container to provide functionality
        the smallest percentage will be returned.

        :param item: BodyPart, model of the item checking.
        :return: float, to 1 decimal place.
        """
        model = item
        if issubclass(item.__class__, ObjectItem):
            model = item.item_model
        actable = model.find_functions('Reload')
        values = [
            act.contains.quantity / act.contains.quantity_max
            for act in actable
        ]
        return 1 - min(values).__round__(1) if values else 0

    def _act_reload(self, action, part, target=None, **kwargs):
        """
        Target is required to be reloaded and requires a free hand to reload
        the target item, when no part is passed then all attached items on
        the character is expected to be reloaded one after the other meaning
        interactions will have to be created for each object.

        To cancel ongoing reloading an action other than another reload or
        movement action is required where these actions would cancel any
        current and future reloading actions.

        This method is expected to manage the readiness state of the character
        as well and will unholster or ready items for manipulation.

        :param action: str, the action happening.
        ;param part: BodyPart, the part interacting to action.
        :param target: BodyPart, optional target to act with.
        """
        holster = 'Holster'
        unholster = 'UnHolster'
        can_reload = {}
        has_free = {}
        manipulator_tally = len(self.manipulators)
        if part:
            if part.contains.items:
                for item in part.contains.items:
                    act = self._act_reload_check_needs(item)
                    if part not in can_reload.keys() or act > can_reload[part]:
                        can_reload[part] = act
            else:
                has_free[part] = True
        for part in self.manipulators:
            if not part.contains.items:
                has_free[part] = True
                continue
            for item in part.contains.items:
                act = self._act_reload_check_needs(item)
                if part not in can_reload.keys() or act > can_reload[part]:
                    can_reload[part] = act
        reload_order = []
        can_reload_keys = list(can_reload.keys())
        can_reload_values = list(can_reload.values())
        while len(can_reload_keys):
            max_value = max(can_reload_values)
            index = can_reload_values.index(max_value)
            if max_value > 0:
                reload_order.append(can_reload_keys[index])
            can_reload_keys.pop(index)
            can_reload_values.pop(index)
        can_reload_keys = list(can_reload.keys())
        free_manipulators = [
            p for p in self.manipulators if p not in reload_order]
        reloader = None
        if free_manipulators:
            for part in free_manipulators:
                if not part.contains.quantity:
                    reloader = part
                    break
            if not reloader:
                reloader = free_manipulators[0]
        elif manipulator_tally >= len(reload_order) >= 2:
            reloader = reload_order[-1:][0]
        if not reloader:
            Middleware.handle('Reload Failure', self, manipulator_tally)
            return
        return_to_ready = reloader.contains.items
        self.act(holster, reloader, target=None)
        self.act(unholster, reloader, target=reloader)
        for part in reload_order:
            if part is reloader:
                self.act(holster, reloader, target=None)
                for item in return_to_ready:
                    self.act(unholster, reloader, target=item)
                reloader = reload_order[0]
                return_to_ready = reloader.contains.items
                self.act(holster, reloader, target=None)
                self.act(unholster, reloader, target=reloader)
            for item in part.contains.items:
                if item in can_reload_keys:
                    interaction = Interaction(self, part, item, action)
                    self.interactions.append(interaction)
        self.act(holster, reloader, target=None)
        for item in return_to_ready:
            self.act(unholster, reloader, target=item)

    def _act_holster(self, action, part, target=None, **kwargs):
        """
        Place all or one item back into a container suitible for the item being
        used in the body part manipulating.

        When 'UnHolster'ing a target is required each time as an insurance to
        what a PlayerCharacter is doing, instead of remembering what was last
        drawn the PlayerCharacter only remembers where items are packed.

        :param action: str, the action happening.
        ;param part: BodyPart, the part interacting to action.
        :param target: BodyPart, optional target to act with.
        """
        index = self.manipulators.index(part)
        if index < 0:
            return
        readied = self.readied[index]
        if action == 'UnHolster' and readied:
            return
        elif action == 'Holster' and not readied:
            return
        elif action == 'ToggleHolster':
            action = '{}{}'.format('Un' if not readied else '', 'Holster')
        for part in self.manipulators:
            items = part.contains.items
            if not readied:
                # take item for readiness
                interaction = Interaction(self, part, None, action)
                if target and target != part and target in self._pack.keys():
                    interaction.item = self._pack[target]
                elif part in self._pack.keys():
                    interaction.item = self._pack[part]
                self.interactions.append(interaction)
            elif items:
                # pack the item away
                self._pack[part] = items
                for item in items:
                    interaction = Interaction(self, item, None, action)
                    if item.type.name == 'Construct':
                        self.interactions.append(interaction)
                        continue
                    if item not in self._pack.keys():
                        pack_loc = self.torso.find_packable(item)
                        self._pack[item] = pack_loc
                    else:
                        pack_loc = self._pack[item]
                    interaction.item = pack_loc
                    interaction.targets = part
                    self.interactions.append(interaction)
            else:
                interaction = Interaction(self, None, None, action)
                interaction.targets = part
                self.interactions.append(interaction)
        self.readied[index] = not readied

    def _act_unholster(self, action, part, target=None, **kwargs):
        """
        When 'UnHolster'ing a target is required only to draw a different
        item from a PlayerCharacters pack, to UnHolster the same item each time
        supply no target.

        To switch to the manipulator itself as the readied object pass the
        target with the same BodyPart manipulator to have that part drawn.

        :param action: str, the action happening.
        ;param part: BodyPart, the part interacting to action.
        :param target: BodyPart, target to act with.
        """
        self._act_holster(action, part, target=target, **kwargs)

    def _act_toggleholster(self, action, part, target=None, **kwargs):
        """
        When 'ToggleHolster'ing a part of the PlayerCharacter the correlating
        target will normally have to be supplied for the expected action.

        :param action: str, the action happening.
        ;param part: BodyPart, the part interacting to action.
        :param target: BodyPart, target to act with.
        """
        self._act_holster(action, part, target=target, **kwargs)

    def act(self, action, part, target=None, **kwargs):
        """
        Have a body part act, this action is derived from the object being
        held and how it is meant to be interacted with, by using the default
        action as a basis the known actions can be automatically applied. For
        actions of the self where no other objects are expected to be a part of
        the act, this means the character is doing something of themselves.
        Examples:
        Talking, Walking, Driving, Jumping, Athletics, Sex, Kung Fu, Aim

        :param action: str, the action expected to be taken.
        :param part: The part of the body expected to act with.
        :param target: optional target character or object to act with.
        """
        method_name = '_act_{}'.format(action.lower().replace(' ', '_'))
        if hasattr(self, method_name):
            getattr(self, method_name)(action, part, target, **kwargs)
        else:
            Middleware.handle(
                'PlayerCharacter Act Unknown',
                self, action, part, target, kwargs
            )

    def _binding_count(self, difference):
        """
        Manage time sensitive bindings.

        :param difference: int, value of time passed.
        """
        keys = list(self._hold_binding.keys())
        for binding in keys:
            if binding == 'last':
                continue
            time = self.binding.time_binding(binding)
            try:
                bound_time = int(self._hold_binding[binding] + difference)
            except KeyError:
                continue
            self._hold_binding[binding] = bound_time
            if binding in ['j', 'k', 'space']:
                if bound_time < rpg_const.JUMP_WAIT and binding == 'space':
                    # TODO: Jump to the fullest amount of effort available.
                    pass
                if bound_time < rpg_const.MELEE_BLOCK_WAIT:
                    continue
                if binding == 'j':
                    # Melee block
                    Middleware.handle('Left Melee Block')
                elif binding == 'k':
                    # Melee block
                    Middleware.handle('Right Melee Block')
            elif time and bound_time >= time:
                if binding == 'r':
                    # Holster weapons and items, ready if holstered.
                    self.binding.skip_binding_up.append(binding)
                    self.act('Holster')
        Middleware.handle('PlayerCharacter Vector', self)

    def _binding_joystick(self, binding, value_1, value_2):
        """
        Movement update depending the movement of a joystick registered to this
        PlayerCharacter bindings.

        :param binding: str, the key change.
        :param value_1: float, diretional value as degrees.
        :param value_2: float, effort being placed into direction.
        """
        Middleware.handle('PlayerCharacter Vector', self)

    def _binding_movement_keyboard(self, binding, key_down=True):
        """
        Process movement of the PlayerCharacter class to update the vector with
        speed and direction along a horizontal plane.

        :param binding: str, the boud key being modified in state.
        :param key_down: bool, True for bindings being pressed, False otherwise.
        """
        held_keys = self._hold_binding.keys()
        found = [c for c in held_keys if c in 'wasd']
        if key_down:
            found.append(binding)
        key = ''.join(found)
        if 'alt' in held_keys and 'shift' in held_keys:
            pass
        elif 'ctrl' not in held_keys:
            if 'shift' in held_keys:
                key += '+'
            if 'alt' in held_keys:
                key += '-'
        else:
            key += '_'
            self.vector.posture = POSTURE_TYPES[2]
        length = len(found)
        if length < 3 and key in MOVEMENT_MAP.keys():
            self.vector = MOVEMENT_MAP[key]
        elif length == 3:
            key = ''
            if 'w' not in found:
                key = 's'
            elif 's' not in found:
                key = 'w'
            elif 'a' not in found:
                key = 'd'
            elif 'd' not in found:
                key = 'a'
            self.vector = MOVEMENT_MAP[key]
        else:
            self.vector = PlayerCharacter.VECTOR_STILL

    def binding_up(self, binding):
        """
        Stop an action from the character.

        All definitions of how this PlayerCharacter should interact is to
        be redefined post MVP.

        :param binding: str, the character representing the key pressed.
        """
        binding = self.binding.known_binding(binding)
        if binding in self.binding.skip_binding_up:
            self.binding.skip_binding_up.remove(binding)
            return
        if binding in self.binding.skip_binding_down:
            self.binding.skip_binding_down.remove(binding)
        # import pdb; pdb.set_trace()
        if binding == 'j':  # 'mouse 1'
            is_with = self.is_interacting_with(self.left_hand)
            # TODO: Post MVP: Update for leg bindings
            for interaction in is_with:
                if interaction.start + interaction.timing > RpgTick.CURRENT:
                    self.stop_interaction(interaction.action, self.left_hand)
        elif binding == 'k':  # 'mouse 2'
            is_with = self.is_interacting_with(self.right_hand)
            # TODO: Post MVP: Update for leg bindings
            for interaction in is_with:
                if interaction.start + interaction.timing > RpgTick.CURRENT:
                    self.stop_interaction(interaction.action, self.right_hand)
        elif binding in ['w', 'a', 's', 'd', 'ctrl', 'shift', 'alt']:
            self._binding_movement_keyboard(binding, key_down=False)
        elif binding in ['Joystick']:
            pass
        else:
            if binding == 'space':
                Middleware.handle('Jump')
            elif binding == 'tab':
                action = 'TAB Menu Hide'
                Middleware.handle(action)
                print(action)
            elif binding == 'r':
                # Reload conventional weapons.
                self.act('Reload', None)
            elif binding == 'v':
                # Stop the charging of Psychic requiring objects
                action = 'Psy Charge'
                found = [i for i in self.interactions if i.action == action]
                for interaction in found:
                    self.interactions.remove(interaction)
            elif binding == 'q':
                # Grenade
                pass
            elif binding == 'wheel press':
                pass
        try:
            self._hold_binding.pop(binding)
        except (ValueError, KeyError, ):
            pass

    def binding_down(self, binding, value_1=None, value_2=None):
        """
        Start an action from the character.

        All definitions of how this PlayerCharacter should interact is to
        be redefined post MVP.

        :param binding: str, the character representing the key pressed.
        :param value_1: float, detail of degree location of joystick.
        :param value_2: float, amount of value added in direction.
        """
        bindings_held = self._hold_binding.keys()
        if binding in bindings_held or self._hold_binding['last'] == binding:
            return
        combat_toggle = 'x'
        holdable = True
        try:
            if binding.index('m ') == 0 and self.character.conscious:
                self.allocate(binding[2:], value_1, int(value_2))
                return
        except (ValueError, AttributeError):
            pass
        if binding == 'VesperRpg System Save':
            """
            Have NPC and Players save their characters independantly at any one
            time, allowing for a difference in state to be taken and updated to
            the stored version of this PlayerCharacter object.
            """
            Middleware.handle('VesperRpg System Save', self)
            return
        elif binding == 'VesperRpg System Exit' and not self.npc:
            rpg_const.SYSTEM_ACTIVE = 0
            Middleware.handle('VesperRpg System Exit', self)
            exit(0)
        binding = self.binding.known_binding(binding)
        if binding not in self.binding.skip_binding_down:
            self.binding.skip_binding_down.append(binding)
        else:
            return
        if not binding:
            return
        if not self.character.conscious:
            return
        if binding == 'j':  # 'mouse 1'
            index = self.manipulators.index(self.left_hand)
            if index < 0:
                return
            if not self.readied[index]:
                for hand in self.manipulators:
                    self.act('UnHolster', hand)
            else:
                is_with = self.left_hand
                if combat_toggle in bindings_held:
                    foot = self.body.find_name(
                        'Left Foot', in_children=True)[-1:]
                    is_with = foot[0]
                self.interact(is_with)
        elif binding == 'k':  # 'mouse 2'
            index = self.manipulators.index(self.right_hand)
            if index < 0:
                return
            if not self.readied[index]:
                for hand in self.manipulators:
                    self.act('UnHolster', hand)
            else:
                is_with = self.right_hand
                if combat_toggle in bindings_held:
                    foot = self.body.find_name(
                        'Right Foot', in_children=True)[-1:]
                    is_with = foot[0]
                self.interact(is_with)
        elif binding in ['w', 'a', 's', 'd', 'ctrl', 'shift', 'alt']:
            self._binding_movement_keyboard(binding)
        elif binding in ['Joystick']:
            pass
        else:
            if binding == 'e':
                if self.vector.targeting:
                    pass
                else:
                    print('No target')
                holdable = False
            elif binding == 'v':
                action = 'Psy Charge'
                indicator = self.character.indicator('Energy')
                psychic = self.character.body.find_functions('Psychic')
                if psychic:
                    for hand in self.manipulators:
                        if len(hand.contains.items):
                            item = hand.contains.items[0]
                            self.act(action, indicator, item)
            elif binding == 'q':
                # Grenade
                pass
            elif binding == 'tab':
                action = 'TAB Menu Show'
                Middleware.handle(action)
                print(action)
            elif binding == 'i':
                Middleware.handle('Inventory Toggle', self)
                holdable = False
            elif binding == 'c':
                Middleware.handle('Character Sheet Toggle', self)
                holdable = False
            elif binding == 't':
                Middleware.handle('Notes')
            elif binding == 'm':
                Middleware.handle('Map')
            elif binding == 'Mouse Wheel Press':
                if not self.readied:
                    for hand in self.manipulators:
                        self.act('UnHolster', hand)
                else:
                    pass
            elif binding == 'Mouse Wheel':
                pass
            else:
                if binding in '1234567890':
                    pass
        if binding and holdable:
            self._hold_binding.update({'last': binding, binding: 0})

    """------------------------------------------------
            === Character creation methods ===
    ------------------------------------------------"""

    def new_soul(self, name='nobody'):
        """
        Every new character requires a soul, part of the initialisation
        for a character.

        :param name: A soul can be provided with a special name before a body
                     is made available to be bound.
        :return: PlayerCharacter
        """
        self.character = CharacterSoul(name=name)
        self.character.id = hash_generate()
        create_character_stats(self.character)
        maps_required = [
            'DISCIPLINES', 'SKILLS', 'ABILITIES', 'DISORDERS', 'PHOBIAS']
        for m in maps_required:
            name = m.lower()
            setattr(
                self.character,
                name,
                duplicate_object(getattr(rpg_const, m))
            )
            stat_group = getattr(self.character, name)
            stat_group.stats = [duplicate_object(s) for s in stat_group.stats]

    def new_life(self, name=''):
        """
        Stage of pre-birth where a character is able to be defined without
        being conscious, useful for defining values without an education.

        :param name: Name of the new body being lived
        :return: CharacterSoul
        """
        if self.character.body:
            raise Exception('Cannot lead a life with two bodies.')
        self.character.body = CharacterBody(
            soul=self.character,
            name=name,
        )
        self.character.available = False
        create_character_body(self.character)
        self.character.body.whole.measure()
        create_character_stats(self.character)

    def _life_stages_points_update(self):
        """
        Helper to convert an education to character statistics.
        # TODO: Separate into CharacterHandler class.
        """
        for stage in self.character.body.life_stages:
            for edu in stage.education:
                for e in edu.teachings:
                    for t in e.cross:
                        name = '{}'.format(t.name.lower())
                        if hasattr(self.character, name):
                            getattr(self.character, name).alloc.append(t)
                            continue
                        stat = self.character.find_stat(t.name)
                        if stat:
                            stat.education.append(t)
                for m in edu.cross_mappings.stats:
                    discipline = self.character.disciplines.find(m.name)
                    if discipline:
                        discipline.education.append(m)
        self.character.social = StatGroup(
            name='Social Traits',
            description='Ability in dexterously navigating life.',
            stats=convert_life_to_social(self)
        )
        self.character.activities = StatGroup(
            name='Active Outlets',
            description='Productive emphases of a character.',
            stats=convert_life_to_activities(self)
        )
        for activity in self.character.activities.stats:
            crosses = []
            for s in rpg_const.SOCIAL_ACTIVITIES.stats:
                if s.name == activity.name:
                    crosses = s.cross
            for cross in crosses:
                stat = self.character.find_stat(cross.name)
                adding = Stat(name=cross.name)
                adding.total = activity.rating * cross.ratio
                stat.education.append(adding)
        self.update()
        self._skills_cross_group()

    def add_life_stages(self):
        """
        Generate the next life stage for this character.
        # TODO: Separate into CharacterHandler class.
        """
        if self.character.body.birth_when < 1:
            raise Exception('Without a birth no life stages can be added.')
        species = self.character.body.species
        try:
            life_stage = duplicate_object(
                species.life_stages[len(self.character.body.life_stages)]
            )
            life_stage.character = self
            self.character.conscious += 1
        except IndexError:
            Middleware.handle('Error', 'Life Stages Exceeded', self)
            return
        create_life_stage_eduction(
            life_stage, self.character.body.life_stages[-1:])
        self.character.body.life_stages.append(life_stage)
        if len(self.character.body.life_stages) < len(species.life_stages):
            self.add_life_stages()
        else:
            self._life_stages_points_update()
            for i in self.character.indicators:
                i.calc_max()

    def birth(self, name=''):
        """
        Have the character be born, allowing for the addition of life stages.

        :param name: str, the name of the character being born.
        """
        if not self.character.body:
            self.new_life()
        rpg_const.CHARACTERS.append(self)
        body = self.character.body
        body.name = name
        body.birth_when = 1
        body.accounts = []
        body.licenses = []
        body.location = rpg_const.LOCATIONS[0]
        birth_certificates = [
            c for c in rpg_const.LICENSES.stats
            if 'Birth' in c.requires and len(c.requires) == 1
        ]
        for license in birth_certificates:
            license = CharacterLicense(body, license.name)
            body.licenses.append(license)
        account_name = '{}\'s {} Account'.format(name, body.location.planet)
        account = CharacterAccount(body, name=account_name)
        body.accounts.append(account)
        self.manipulators = body.find_functions('Manipulation')
        self.readied = [False] * len(self.manipulators)
        self.torso = self.body.find_name('Body')
        if not self.torso:
            replacements = self.body.find_affect('Replaces')
            for item in replacements:
                affects = [i.ratio for i in item.affect]
                if 'Body' in affects:
                    self.torso = item
                    self.torso.affect.append(
                        StatType(name='Replaced', ratio=self.torso.name))
                    self.torso.name = 'Body'
                    break
        if not self.torso:
            raise Exception("Failed to find replacement part for 'Body'")
        elif type(self.torso) is list:
            self.torso = self.torso[0]
        self.vector = BodyVector(
            speed=MOVEMENT_TYPES[4],
            posture=POSTURE_TYPES[0],
        )
        self.vectors_incoming = []
        Middleware.handle('PlayerCharacter Vector', self)
        # TODO: Post MVP. Life stages of a construct body are minimal to 0.
        # TODO: Post MVP. Restrictions of multiple life stat point allocations.
        self.add_life_stages()
        self._reset_indicators()
        self.update()
        self.interactions.append(Interaction(self, None, None, 'Affects'))
        Middleware.handle('Birth', self)

    def death(self):
        """
        Kill the body of this character.
        """
        self.interactions = []
        self.character.conscious -= len(self.character.body.species.life_stages)
        self.character.bound_bodies.append(self.character.body)
        self.character.body = None
        self.character.stats = self.character.stats_soul
        self.character.available = True
        Middleware.handle('Death', self)

    def update(self):
        """Update all stats of this character."""
        self.character.stats.consolidate()
        self.character.stats.update()
        self.character.disciplines.consolidate()
        self.character.disciplines.update()
        self.character.skills.consolidate()
        self.character.skills.update()

    def __init__(self, nobody=False, save_id=None, npc=True, *args, **kwargs):
        self.interactions = []
        self.feedback_queue = []
        self._hold_binding = {'last': ''}
        self._pack = {}
        self.npc = npc
        self.binding = Binding(self)
        self.new_soul()
        if not save_id:
            if not nobody:
                self.new_life()
            self.binding_down('VesperRpg System Save')
        else:
            self.character.id = save_id
            Middleware.handle('PlayerCharacter Load', self)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return '<PlayerCharacter "{}", type: {}, stage: {}>'.format(
            self.name,
            'Player' if self.binding else 'NPC',
            len(self.character.body.life_stages),
        )
