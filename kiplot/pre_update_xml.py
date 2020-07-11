from sys import exit
from subprocess import call
from kiplot.macros import macros, pre_class  # noqa: F401
from kiplot.pre_base import BasePreFlight
from kiplot.error import KiPlotConfigurationError
from kiplot.gs import GS
from kiplot.kiplot import check_eeschema_do
from kiplot.misc import CMD_EESCHEMA_DO, BOM_ERROR
from kiplot.log import get_logger

logger = get_logger(__name__)


@pre_class
class Update_XML(BasePreFlight):
    """ [boolean=false] Update the XML version of the BoM (Bill of Materials). To ensure our generated BoM is up to date """
    def __init__(self, name, value):
        super().__init__(name, value)
        if not isinstance(value, bool):
            raise KiPlotConfigurationError('must be boolean')
        self._enabled = value
        self._sch_related = True

    def run(self):
        check_eeschema_do()
        cmd = [CMD_EESCHEMA_DO, 'bom_xml', GS.sch_file, GS.out_dir]
        # If we are in verbose mode enable debug in the child
        if GS.debug_enabled:
            cmd.insert(1, '-vv')
            cmd.insert(1, '-r')
        logger.info('- Updating BoM in XML format')
        logger.debug('Executing: '+str(cmd))
        ret = call(cmd)
        if ret:
            logger.error('Failed to update the BoM, error %d', ret)
            exit(BOM_ERROR)
