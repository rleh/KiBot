from pcbnew import EXCELLON_WRITER
from kiplot.out_any_drill import AnyDrill
from kiplot.out_base import BaseOutput
from kiplot.macros import macros, document, output_class  # noqa: F401


class ExcellonOptions(AnyDrill):
    def __init__(self):
        super().__init__()
        with document:
            self.metric_units = True
            """ use metric units instead of inches """
            self.pth_and_npth_single_file = True
            """ generate one file for both, plated holes and non-plated holes, instead of two separated files """
            self.minimal_header = False
            """ use a minimal header in the file """
            self.mirror_y_axis = False
            """ invert the Y axis """  # pragma: no cover

    def _configure_writer(self, board, offset):
        drill_writer = EXCELLON_WRITER(board)
        drill_writer.SetOptions(self.mirror_y_axis, self.minimal_header, offset, self.pth_and_npth_single_file)
        drill_writer.SetFormat(self.metric_units, EXCELLON_WRITER.DECIMAL_FORMAT)
        return drill_writer


@output_class
class Excellon(BaseOutput):
    """ Excellon drill format
        This is the main format for the drilling machine.
        You can create a map file for documentation purposes.
        This output is what you get from the 'File/Fabrication output/Drill Files' menu in pcbnew. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = ExcellonOptions
            """ [dict] Options for the `excellon` output """  # pragma: no cover
