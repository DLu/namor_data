from metro_db import MetroDB
import pathlib
from enum import IntEnum, IntFlag, auto


class Relationship(IntEnum):
    IS_SHORT_FOR = 1
    ORIGINATES_FROM = 2
    IS_A_VARIANT_OF = 3
    IS_EQUIVALENT_TO = 4
    IS_TRANSLITERATED_AS = 5

    @staticmethod
    def lookup(s):
        if s == 'var' or s == 'varform':
            return Relationship.IS_A_VARIANT_OF
        elif s == 'eq':
            return Relationship.IS_EQUIVALENT_TO
        elif s == 'dim' or s == 'diminutive':
            return Relationship.IS_SHORT_FOR


class GenderFlag(IntFlag):
    FEMALE = auto()
    MALE = auto()
    UNISEX = auto()


class WiktionaryDB(MetroDB):
    def __init__(self):
        MetroDB.__init__(self, 'wiktionary', folder=pathlib.Path(__file__).parent, enums_to_register=[Relationship])
