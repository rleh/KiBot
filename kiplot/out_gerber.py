from pcbnew import (PLOT_FORMAT_GERBER, FromMM, ToMM)
from kiplot.out_any_layer import (AnyLayer, AnyLayerOptions)
from kiplot.error import KiPlotConfigurationError
from kiplot.macros import macros, document, output_class  # noqa: F401


class GerberOptions(AnyLayerOptions):
    def __init__(self):
        super().__init__()
        self._plot_format = PLOT_FORMAT_GERBER
        with document:
            self.use_aux_axis_as_origin = False
            """ use the auxiliar axis as origin for coordinates """
            self.line_width = 0.1
            """ [0.02,2] line_width for objects without width [mm] """
            self.subtract_mask_from_silk = False
            """ substract the solder mask from the silk screen """
            self.use_protel_extensions = False
            """ use legacy Protel file extensions """
            self._gerber_precision = 4.6
            """ this the gerber coordinate format, can be 4.5 or 4.6 """
            self.create_gerber_job_file = True
            """ creates a file with information about all the generated gerbers.
                You can use it in gerbview to load all gerbers at once """
            self.use_gerber_x2_attributes = True
            """ use the extended X2 format """
            self.use_gerber_net_attributes = True
            """ include netlist metadata """  # pragma: no cover

    @property
    def gerber_precision(self):
        return self._gerber_precision

    @gerber_precision.setter
    def gerber_precision(self, val):
        if val != 4.5 and val != 4.6:
            raise KiPlotConfigurationError("`gerber_precision` must be 4.5 or 4.6")
        self._gerber_precision = val

    def _configure_plot_ctrl(self, po, output_dir):
        super()._configure_plot_ctrl(po, output_dir)
        po.SetSubtractMaskFromSilk(self.subtract_mask_from_silk)
        po.SetUseGerberProtelExtensions(self.use_protel_extensions)
        po.SetGerberPrecision(5 if self.gerber_precision == 4.5 else 6)
        po.SetCreateGerberJobFile(self.create_gerber_job_file)
        po.SetUseGerberX2format(self.use_gerber_x2_attributes)
        po.SetIncludeGerberNetlistInfo(self.use_gerber_net_attributes)
        po.SetUseAuxOrigin(self.use_aux_axis_as_origin)
        po.SetLineWidth(FromMM(self.line_width))

    def read_vals_from_po(self, po):
        super().read_vals_from_po(po)
        # usegerberattributes
        self.use_gerber_x2_attributes = po.GetUseGerberX2format()
        # usegerberextensions
        self.use_protel_extensions = po.GetUseGerberProtelExtensions()
        # usegerberadvancedattributes
        self.use_gerber_net_attributes = po.GetIncludeGerberNetlistInfo()
        # creategerberjobfile
        self.create_gerber_job_file = po.GetCreateGerberJobFile()
        # gerberprecision
        self.gerber_precision = 4.0 + po.GetGerberPrecision()/10.0
        # subtractmaskfromsilk
        self.subtract_mask_from_silk = po.GetSubtractMaskFromSilk()
        # useauxorigin
        self.use_aux_axis_as_origin = po.GetUseAuxOrigin()
        # linewidth
        self.line_width = ToMM(po.GetLineWidth())


@output_class
class Gerber(AnyLayer):
    """ Gerber format
        This is the main fabrication format for the PCB.
        This output is what you get from the File/Plot menu in pcbnew. """
    def __init__(self):
        super().__init__()
        with document:
            self.options = GerberOptions
            """ [dict] Options for the `gerber` output """  # pragma: no cover
