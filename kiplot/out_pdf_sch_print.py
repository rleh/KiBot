import os
from subprocess import call
from kiplot.gs import GS
from kiplot.kiplot import check_eeschema_do
from kiplot.misc import CMD_EESCHEMA_DO, PDF_SCH_PRINT
from kiplot.optionable import BaseOptions
from kiplot.out_base import BaseOutput
from kiplot.macros import macros, document, output_class  # noqa: F401
from kiplot.log import get_logger

logger = get_logger(__name__)


class PDF_Sch_PrintOptions(BaseOptions):
    def __init__(self):
        super().__init__()
        with document:
            self.output = ''
            """ filename for the output PDF (the name of the schematic if empty) """  # pragma: no cover

    def run(self, output_dir, board):
        check_eeschema_do()
        cmd = [CMD_EESCHEMA_DO, 'export', '--all_pages', '--file_format', 'pdf', GS.sch_file, output_dir]
        if GS.debug_enabled:
            cmd.insert(1, '-vv')
            cmd.insert(1, '-r')
        logger.debug('Executing: '+str(cmd))
        ret = call(cmd)
        if ret:
            logger.error(CMD_EESCHEMA_DO+' returned %d', ret)
            exit(PDF_SCH_PRINT)
        if self.output:
            cur = os.path.abspath(os.path.join(output_dir, os.path.splitext(os.path.basename(GS.pcb_file))[0]) + '.pdf')
            new = os.path.abspath(os.path.join(output_dir, self.output))
            logger.debug('Moving '+cur+' -> '+new)
            os.rename(cur, new)


@output_class
class PDF_Sch_Print(BaseOutput):
    """ PDF Schematic Print (Portable Document Format)
        Exports the PCB to the most common exhange format. Suitable for printing.
        This is the main format to document your schematic.
        This output is what you get from the 'File/Print' menu in eeschema. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = PDF_Sch_PrintOptions
            """ [dict] Options for the `pdf_sch_print` output """  # pragma: no cover
        self._sch_related = True
