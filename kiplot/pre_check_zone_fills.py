from kiplot.error import KiPlotConfigurationError
from kiplot.pre_base import BasePreFlight
from kiplot.macros import macros, pre_class  # noqa: F401


@pre_class
class Check_Zone_Fills(BasePreFlight):
    """ [boolean=false] Zones are filled before doing any operation involving PCB layers """
    def __init__(self, name, value):
        super().__init__(name, value)
        if not isinstance(value, bool):
            raise KiPlotConfigurationError('must be boolean')
        self._enabled = value

    def apply(self):
        BasePreFlight._set_option('check_zone_fills', self._enabled)
