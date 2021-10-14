import copy
from collections import namedtuple

import numpy as np
from ophyd.device import Component as Cpt
from ophyd.positioner import SoftPositioner

from .device import GroupDevice
from .epics_motor import BeckhoffAxis
from .interface import FltMvInterface
from .pseudopos import PseudoPositioner, PseudoSingleInterface
from .signal import InternalSignal


class QuadraticBeckhoffMotor(FltMvInterface, PseudoPositioner):
    """
    Calc = ax^2 + bx + c
    """
    calc = Cpt(PseudoSingleInterface, egu='mrad', kind='hinted')
    real = Cpt(BeckhoffAxis, '', kind='omitted')

    # Aux signals for the typhos screen
    high_limit_travel = Cpt(InternalSignal, kind='omitted')
    low_limit_travel = Cpt(InternalSignal, kind='omitted')

    def __init__(self, prefix, *, name, ca, cb, cc, pol, limits, **kwargs):
        self.ca = ca
        self.cb = cb
        self.cc = cc
        self.pol = pol
        super().__init__(prefix, name=name, **kwargs)
        self.calc._limits = limits
        self.low_limit_travel.put(limits[0], force=True)
        self.high_limit_travel.put(limits[1], force=True)

    def forward(self, pseudo_pos: namedtuple) -> namedtuple:
        """
        Called to calc desired real using given mrad when we move
        """
        calc = pseudo_pos.calc
        real = (
            -self.cb
            + self.pol * np.sqrt(self.cb**2 - 4*self.ca*(self.cc - calc))
            ) / (2*self.ca)
        return self.RealPosition(real=real)

    def inverse(self, real_pos: namedtuple) -> namedtuple:
        """
        Called to calc the mrad using the current real when we get position
        """
        real = real_pos.real
        calc = self.ca * real**2 + self.cb * real + self.cc
        return self.PseudoPosition(calc=calc)


class QuadraticSimMotor(QuadraticBeckhoffMotor):
    real = Cpt(SoftPositioner, kind='omitted')


class VLSOptics(GroupDevice):
    mirror = Cpt(
        QuadraticBeckhoffMotor,
        "CRIX:VLS:MMS:MP",
        ca=-0.2479,
        cb=18.09,
        cc=33.85,
        pol=1,
        limits=(-31.99, 41.42),
        kind='hinted',
    )
    grating = Cpt(
        QuadraticBeckhoffMotor,
        "CRIX:VLS:MMS:GP",
        ca=0.334,
        cb=-16.25,
        cc=22.56,
        pol=-1,
        limits=(3.541, 51.8462),
        kind='hinted',
    )


class VLSOpticsSim(VLSOptics):
    mirror = copy.copy(VLSOptics.mirror)
    mirror.cls = QuadraticSimMotor
    grating = copy.copy(VLSOptics.grating)
    grating.cls = QuadraticSimMotor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mirror.real.move(0)
        self.grating.real.move(20)
