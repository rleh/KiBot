# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 Salvador E. Tropea
# Copyright (c) 2020-2021 Instituto Nacional de Tecnología Industrial
# License: GPL-3.0
# Project: KiBot (formerly KiPlot)
# The algorithm is from KiCost project (https://github.com/xesscorp/KiCost)
"""
Implements the KiCost variants mechanism.
"""
import re
from .gs import GS
from .misc import IFILT_VAR_RENAME_KICOST, IFILT_KICOST_RENAME, IFILT_KICOST_DNP
from .fil_base import BaseFilter
from .macros import macros, document, variant_class  # noqa: F401
from . import log

logger = log.get_logger(__name__)


@variant_class
class KiCost(BaseVariant):  # noqa: F821
    """ KiCost variant style
        The `variant` field (configurable) contains one or more values.
        If any of these values matches the variant regex the component is included.
        By default a pre-transform filter is applied to support kicost.VARIANT:FIELD and
        field name aliases used by KiCost.
        Also a default `dnf_filter` implements the KiCost DNP mechanism """
    def __init__(self):
        super().__init__()
        with document:
            self.variant = ''
            """ Variants to match (regex) """
            self.variant_field = 'variant'
            """ Name of the field that stores board variant/s for component """
            self.separators = ',;/ '
            """ Valid separators for variants in the variant field.
                Each character is a valid separator """

    def get_variant_field(self):
        ''' Returns the name of the field used to determine if the component belongs to teh variant '''
        return self.variant_field

    def config(self, parent):
        super().config(parent)
        self.pre_transform = BaseFilter.solve_filter(self.pre_transform, 'pre_transform',
                                                     [IFILT_VAR_RENAME_KICOST, IFILT_KICOST_RENAME], is_transform=True)
        self.exclude_filter = BaseFilter.solve_filter(self.exclude_filter, 'exclude_filter')
        self.dnf_filter = BaseFilter.solve_filter(self.dnf_filter, 'dnf_filter', IFILT_KICOST_DNP)
        self.dnc_filter = BaseFilter.solve_filter(self.dnc_filter, 'dnc_filter')
        if not self.separators:
            self.separators = ' '
        else:
            self.separators = '['+self.separators+']'

    def filter(self, comps):
        GS.variant = [self.variant]
        comps = super().filter(comps)
        logger.debug("Applying KiCost style variant `{}`".format(self.name))
        if not self.variant_field or not self.variant:
            # No variant field or not variant regex
            # Just skip the process
            return comps
        # Apply to all the components
        var_re = re.compile(self.variant, flags=re.IGNORECASE)
        for c in comps:
            logger.debug("{} {} {}".format(c.ref, c.fitted, c.included))
            if not (c.fitted and c.included):
                # Don't check if we already discarded it
                continue
            variants = c.get_field_value(self.variant_field)
            if variants:
                # The component belong to one or more variant
                for v in re.split(self.separators, variants):
                    if var_re.match(v):
                        # Matched, remains
                        break
                else:
                    # None of the variants matched
                    c.fitted = False
                    if GS.debug_level > 2:
                        logger.debug('ref: {} value: {} -> False'.format(c.ref, c.value))
        return comps
