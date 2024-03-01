import pyEDAA.ProjectModel as pm

from typing import Set


class UsedIn(pm.Attribute):
    NAME: 'UsedIn'
    VALUE_TYPE: Set[str]
