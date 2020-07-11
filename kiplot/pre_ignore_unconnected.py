from kiplot.macros import macros, pre_class  # noqa: F401
from kiplot.pre_base import BasePreFlight
from kiplot.error import KiPlotConfigurationError


@pre_class
class Ignore_Unconnected(BasePreFlight):
    """ [boolean=false] Option for `run_drc`. Ignores the unconnected nets. Useful if you didn't finish the routing """
    def __init__(self, name, value):
        super().__init__(name, value)
        if not isinstance(value, bool):
            raise KiPlotConfigurationError('must be boolean')
        self._enabled = value

    def get_example():
        """ Returns a YAML value for the example config """
        return 'false'

    def apply(self):
        BasePreFlight._set_option('ignore_unconnected', self._enabled)
