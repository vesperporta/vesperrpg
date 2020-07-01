"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence Psychic
Email: vesper.porta@protonmail.com

Data built into VesperRpg System.
"""

from models import BodyVector


POSTURE_TYPES = [
    ('Standing', 1),
    ('Bowing', 0.8),
    ('Crouching', 0.6),
    ('Laying', 0.2),
]

MOVEMENT_TYPES = [
    ('Sprint', 8),
    ('Paced', 5),
    ('Walking', 3.5),
    ('Crawl', 1.2),
    ('Still', 0),
]

COMBAT_TYPES = [
    ('Fist', 1),
    ('Feet', 2),
]

MOVEMENT_MAP = {
    'w': BodyVector(
        speed=('Paced', 5),
        direction=0,
    ),
    's': BodyVector(
        speed=('Walking', 3.5),
        direction=180,
    ),
    'a': BodyVector(
        speed=('Paced', 5),
        direction=270,
    ),
    'd': BodyVector(
        speed=('Paced', 5),
        direction=90,
    ),
    'wa': BodyVector(
        speed=('Paced', 5),
        direction=315,
    ),
    'wd': BodyVector(
        speed=('Paced', 5),
        direction=45,
    ),
    'sa': BodyVector(
        speed=('Walking', 3.5),
        direction=225,
    ),
    'sd': BodyVector(
        speed=('Walking', 3.5),
        direction=135,
    ),
    'aw': BodyVector(
        speed=('Paced', 5),
        direction=315,
    ),
    'dw': BodyVector(
        speed=('Paced', 5),
        direction=45,
    ),
    'as': BodyVector(
        speed=('Walking', 3.5),
        direction=225,
    ),
    'ds': BodyVector(
        speed=('Walking', 3.5),
        direction=135,
    ),

    'w+': BodyVector(
        speed=('Sprint', 8),
        direction=0,
    ),
    's+': BodyVector(
        speed=('Paced', 5),
        direction=180,
    ),
    'a+': BodyVector(
        speed=('Sprint', 8),
        direction=270,
    ),
    'd+': BodyVector(
        speed=('Sprint', 8),
        direction=90,
    ),
    'wa+': BodyVector(
        speed=('Sprint', 6),
        direction=335,
    ),
    'wd+': BodyVector(
        speed=('Sprint', 6),
        direction=25,
    ),
    'sa+': BodyVector(
        speed=('Paced', 5),
        direction=225,
    ),
    'sd+': BodyVector(
        speed=('Paced', 5),
        direction=135,
    ),
    'aw+': BodyVector(
        speed=('Sprint', 6),
        direction=335,
    ),
    'dw+': BodyVector(
        speed=('Sprint', 6),
        direction=25,
    ),
    'as+': BodyVector(
        speed=('Paced', 5),
        direction=225,
    ),
    'ds+': BodyVector(
        speed=('Paced', 5),
        direction=135,
    ),

    'w-': BodyVector(
        speed=('Walking', 3.5),
        direction=0,
    ),
    's-': BodyVector(
        speed=('Crawl', 1.2),
        direction=180,
    ),
    'a-': BodyVector(
        speed=('Walking', 3.5),
        direction=270,
    ),
    'd-': BodyVector(
        speed=('Walking', 3.5),
        direction=90,
    ),
    'wa-': BodyVector(
        speed=('Walking', 3.5),
        direction=315,
    ),
    'wd-': BodyVector(
        speed=('Walking', 3.5),
        direction=45,
    ),
    'sa-': BodyVector(
        speed=('Crawl', 1.2),
        direction=225,
    ),
    'sd-': BodyVector(
        speed=('Crawl', 1.2),
        direction=135,
    ),
    'aw-': BodyVector(
        speed=('Walking', 3.5),
        direction=315,
    ),
    'dw-': BodyVector(
        speed=('Walking', 3.5),
        direction=45,
    ),
    'as-': BodyVector(
        speed=('Crawl', 1.2),
        direction=225,
    ),
    'ds-': BodyVector(
        speed=('Crawl', 1.2),
        direction=135,
    ),

    'w_': BodyVector(
        speed=('Crawl', 1.2),
        direction=0,
    ),
    's_': BodyVector(
        speed=('Crawl', 1.2),
        direction=180,
    ),
    'a_': BodyVector(
        speed=('Crawl', 1.2),
        direction=270,
    ),
    'd_': BodyVector(
        speed=('Crawl', 1.2),
        direction=90,
    ),
    'wa_': BodyVector(
        speed=('Crawl', 1.2),
        direction=315,
    ),
    'wd_': BodyVector(
        speed=('Crawl', 1.2),
        direction=45,
    ),
    'sa_': BodyVector(
        speed=('Crawl', 1.2),
        direction=225,
    ),
    'sd_': BodyVector(
        speed=('Crawl', 1.2),
        direction=135,
    ),
    'aw_': BodyVector(
        speed=('Crawl', 1.2),
        direction=315,
    ),
    'dw_': BodyVector(
        speed=('Crawl', 1.2),
        direction=45,
    ),
    'as_': BodyVector(
        speed=('Crawl', 1.2),
        direction=225,
    ),
    'ds_': BodyVector(
        speed=('Crawl', 1.2),
        direction=135,
    ),
}
