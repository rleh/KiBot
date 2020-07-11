from pcbnew import (PLOT_FORMAT_PDF, FromMM, ToMM)
from kiplot.out_any_layer import AnyLayer
from kiplot.drill_marks import DrillMarks
from kiplot.macros import macros, document, output_class  # noqa: F401
from kiplot.log import get_logger

logger = get_logger(__name__)


class PDFOptions(DrillMarks):
    def __init__(self):
        super().__init__()
        with document:
            self.line_width = 0.1
            """ [0.02,2] for objects without width [mm] """
            self.mirror_plot = False
            """ plot mirrored """
            self.negative_plot = False
            """ invert black and white """  # pragma: no cover
        self._plot_format = PLOT_FORMAT_PDF

    def _configure_plot_ctrl(self, po, output_dir):
        super()._configure_plot_ctrl(po, output_dir)
        po.SetMirror(self.mirror_plot)
        po.SetLineWidth(FromMM(self.line_width))
        po.SetNegative(self.negative_plot)

    def read_vals_from_po(self, po):
        super().read_vals_from_po(po)
        self.mirror_plot = po.GetMirror()
        self.line_width = ToMM(po.GetLineWidth())
        self.negative_plot = po.GetNegative()


@output_class
class PDF(AnyLayer, DrillMarks):
    """ PDF (Portable Document Format)
        Exports the PCB to the most common exhange format. Suitable for printing.
        Note that this output isn't the best for documating your project.
        This output is what you get from the File/Plot menu in pcbnew. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = PDFOptions
            """ [dict] Options for the `pdf` output """  # pragma: no cover
