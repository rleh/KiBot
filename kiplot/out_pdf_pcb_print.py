import os
from subprocess import (call)
from kiplot.pre_base import BasePreFlight
from kiplot.error import KiPlotConfigurationError
from kiplot.gs import GS
from kiplot.kiplot import check_script
from kiplot.misc import CMD_PCBNEW_PRINT_LAYERS, URL_PCBNEW_PRINT_LAYERS, PDF_PCB_PRINT
from kiplot.optionable import BaseOptions
from kiplot.out_base import BaseOutput
from kiplot.macros import macros, document, output_class  # noqa: F401
from kiplot.layer import Layer
from kiplot.log import get_logger

logger = get_logger(__name__)


class PDF_Pcb_PrintOptions(BaseOptions):
    def __init__(self):
        super().__init__()
        with document:
            self.output_name = ''
            """ filename for the output PDF (the name of the PCB if empty) """  # pragma: no cover

    def run(self, output_dir, board, layers):
        check_script(CMD_PCBNEW_PRINT_LAYERS, URL_PCBNEW_PRINT_LAYERS, '1.4.1')
        # Output file name
        output = self.output_name
        if not output:
            output = os.path.splitext(os.path.basename(GS.pcb_file))[0]+'.pdf'
        output = os.path.abspath(os.path.join(output_dir, output))
        cmd = [CMD_PCBNEW_PRINT_LAYERS, 'export', '--output_name', output]
        if BasePreFlight.get_option('check_zone_fills'):
            cmd.append('-f')
        cmd.extend([GS.pcb_file, output_dir])
        if GS.debug_enabled:
            cmd.insert(1, '-vv')
            cmd.insert(1, '-r')
        # Add the layers
        layers = Layer.solve(layers)
        cmd.extend([l.layer for l in layers])
        # Execute it
        logger.debug('Executing: '+str(cmd))
        ret = call(cmd)
        if ret:  # pragma: no cover
            # We check all the arguments, we even load the PCB
            # A fail here isn't easy to reproduce
            logger.error(CMD_PCBNEW_PRINT_LAYERS+' returned %d', ret)
            exit(PDF_PCB_PRINT)


@output_class
class PDF_Pcb_Print(BaseOutput):
    """ PDF PCB Print (Portable Document Format)
        Exports the PCB to the most common exhange format. Suitable for printing.
        This is the main format to document your PCB.
        This output is what you get from the 'File/Print' menu in pcbnew. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = PDF_Pcb_PrintOptions
            """ [dict] Options for the `pdf_pcb_print` output """
            self.layers = Layer
            """ [list(dict)|list(string)|string] [all,selected,copper,technical,user]
                List of PCB layers to include in the PDF """  # pragma: no cover

    def config(self, tree):
        super().config(tree)
        # We need layers
        if isinstance(self.layers, type):
            raise KiPlotConfigurationError("Missing `layers` list")

    def run(self, output_dir, board):
        self.options.run(output_dir, board, self.layers)
