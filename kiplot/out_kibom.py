import os
from glob import glob
from subprocess import (check_output, STDOUT, CalledProcessError)
from kiplot.misc import (CMD_KIBOM, URL_KIBOM, BOM_ERROR)
from kiplot.kiplot import check_script
from kiplot.gs import GS
from kiplot.optionable import BaseOptions
from kiplot.out_base import BaseOutput
from kiplot.macros import macros, document, output_class  # noqa: F401
from . import log

logger = log.get_logger(__name__)


class KiBoMOptions(BaseOptions):
    def __init__(self):
        super().__init__()
        with document:
            self.number = 1
            """ Number of boards to build (components multiplier) """
            self.variant = ''
            """ Board variant(s), used to determine which components
                are output to the BoM. To specify multiple variants,
                with a BOM file exported for each variant, separate
                variants with the ';' (semicolon) character """
            self.conf = 'bom.ini'
            """ BoM configuration file, relative to PCB """
            self.separator = ','
            """ CSV Separator """
            self.format = 'HTML'
            """ [HTML,CSV] format for the BoM """  # pragma: no cover

    def run(self, output_dir, board):
        check_script(CMD_KIBOM, URL_KIBOM)
        format = self.format.lower()
        prj = os.path.splitext(os.path.abspath(GS.pcb_file))[0]
        config = os.path.join(os.path.dirname(os.path.abspath(GS.pcb_file)), self.conf)
        logger.debug('Doing BoM, format {} prj: {} config: {}'.format(format, prj, config))
        cmd = [CMD_KIBOM,
               '-n', str(self.number),
               '--cfg', config,
               '-s', self.separator]
        if GS.debug_enabled:
            cmd.append('-v')
        if self.variant:
            cmd.extend(['-r', self.variant])
        cmd.extend([prj+'.xml', os.path.join(output_dir, os.path.basename(prj))+'.'+format])
        logger.debug('Running: '+str(cmd))
        try:
            cmd_output = check_output(cmd, stderr=STDOUT)
        except CalledProcessError as e:
            logger.error('Failed to create BoM, error %d', e.returncode)
            if e.output:
                logger.debug('Output from command: '+e.output.decode())
            exit(BOM_ERROR)
        prj = os.path.basename(prj)
        for f in glob(os.path.join(output_dir, prj)+'*.tmp'):
            # I'm not sure when these files are left, but they are annoying
            os.remove(f)  # pragma: no cover
        logger.debug('Output from command:\n'+cmd_output.decode())


@output_class
class KiBoM(BaseOutput):
    """ KiBoM (KiCad Bill of Materials)
        Used to generate the BoM in HTML or CSV format using the KiBoM plug-in.
        For more information: https://github.com/INTI-CMNB/KiBoM
        This output is what you get from the 'Tools/Generate Bill of Materials' menu in eeschema. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = KiBoMOptions
            """ [dict] Options for the `kibom` output """  # pragma: no cover
        self._sch_related = True
