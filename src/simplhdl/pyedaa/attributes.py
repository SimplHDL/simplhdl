import pyEDAA.ProjectModel as pm

from typing import Set

SIMULATION = "simulation"
IMPLEMENTATION = "implementation"


class UsedIn(pm.Attribute):
    NAME: 'UsedIn'
    VALUE_TYPE: Set[str]


class Encrypt(pm.Attribute):
    NAME: 'Encrypt'
    VALUE_TYPE: bool


class Scope(pm.Attribute):
    NAME: 'Scope'
    VALUE_TYPE: str
