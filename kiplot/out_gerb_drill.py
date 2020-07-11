from pcbnew import GERBER_WRITER
from kiplot.out_any_drill import AnyDrill
from kiplot.out_base import BaseOutput
from kiplot.macros import macros, document, output_class  # noqa: F401


class Gerb_DrillOptions(AnyDrill):
    def __init__(self):
        super().__init__()

    def _configure_writer(self, board, offset):
        drill_writer = GERBER_WRITER(board)
        # hard coded in UI?
        drill_writer.SetFormat(5)
        drill_writer.SetOptions(offset)
        return drill_writer


@output_class
class Gerb_Drill(BaseOutput):
    """ Gerber drill format
        This is the information for the drilling machine in gerber format.
        You can create a map file for documentation purposes.
        This output is what you get from the 'File/Fabrication output/Drill Files' menu in pcbnew. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = Gerb_DrillOptions
            """ [dict] Options for the `gerb_drill` output """  # pragma: no cover
