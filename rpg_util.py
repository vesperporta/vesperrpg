"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence Psychic
Email: vesper.porta@protonmail.com

Utilitise required through VesperRpg System.
"""

from math import cos, pi
from random import choice


def copy_object(obj, target, skip=[]):
    """
    Copy an object attribute for attribute.
    Restrictions of this form of copy is a shallow copy.
    Lists will just be sliced and objects within are not duplicated.
    """
    for i in obj.__dict__:
        if i in skip:
            continue
        attr = getattr(obj, i)
        if type(attr) is list:
            attr = attr[:]
        setattr(target, i, attr)
    return target


def duplicate_object(obj, target=None, deep=False, skip=[], default=None):
    """Copy an object attribute for attribute."""
    if not obj:
        return default
    if type(obj) is list:
        return [
            duplicate_object(o, deep=True, skip=skip) for o in obj
        ] if deep else obj[:]
    if type(obj) is str:
        return '{}'.format(obj)
    if not target:
        rtn = obj.__class__()
    else:
        rtn = target
    return copy_object(obj, rtn, skip=skip)


def mass_to_energy(mass):
    """Convert mass KG into Joules J or E=mc2"""
    return float(mass) * (299790000 * 299790000)


def energy_to_mass(energy):
    """Convert Joules J into mass KG or E=mc2"""
    return energy / (299790000 * 299790000)


def schwarzschild_radius(mass):
    """The radius of a black hole determined by the mass of the black hole."""
    return 2 * 0.00000000000667408 * float(mass) / (299790000 * 299790000)


def impact_velocity(distance, measure_0, measure_152):
    """Impact velocity for a given distance."""
    distance_152 = 152.4
    return float(
        (
            ((measure_0 - measure_152) / distance_152) *
            distance_152 - distance
        ) + measure_152
    )


def impact_energy(mass, velocity):
    """Impact energy."""
    return 0.5 * mass * (velocity * velocity)


def ease_mult(t, d):
    """
    Method to supply an easing 'S' shape to variables.

    :param t: The variable to check against the determinate value
    :param d: The determinate value.
    :return: float
    """
    i = 0
    negative = False
    if (d < 0 and t > 0) or (t < 0 and d > 0):
        negative = True
    if t > d and d > 0:
        i = int(t / d)
        t = t % d
    rtn = (-0.5 * (cos(pi * t / d) - 1)) + i if d != 0 else 0
    return rtn if not negative else rtn * -1


def ease_mult_cap(t, d):
    if d < 0 and t < d:
        t = d
        t = 0
    if t > d:
        t = d
    return ease_mult(t, d)


def hash_generate(length=24):
    i = 0
    length = 16
    rtn = ''
    while i < length:
        i += 1
        rtn += chr(choice(range(97, 122)))
    return rtn


class Middleware(object):
    """
    Inheritable class to create a middleware object registered within the
    VesperRPG System.
    """
    _REGISTERED = {}

    name = None

    @staticmethod
    def handle(calling, *args, chain_return=None, **kwargs):
        rtn = chain_return
        if calling not in Middleware._REGISTERED.keys():
            return
        rtn = Middleware._REGISTERED[calling].action(
            *args, chain_return=rtn, **kwargs
        )
        return rtn

    def action(self, *args, chain_return=None, **kwargs):
        """
        Handle your middleware call here.
        Must be overridden.
        """
        return chain_return

    def register(self):
        Middleware._REGISTERED.update({self.name: self})

    def unregister(self):
        Middleware._REGISTERED.remove(self.name)

    def __init__(self, name):
        self.name = name
        self.register()
