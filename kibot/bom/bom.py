# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 Salvador E. Tropea
# Copyright (c) 2020-2021 Instituto Nacional de Tecnología Industrial
# Copyright (c) 2016-2020 Oliver Henry Walters (@SchrodingersGat)
# License: MIT
# Project: KiBot (formerly KiPlot)
# Adapted from: https://github.com/SchrodingersGat/KiBoM
# Contributors: Kenny Huynh (@hkennyv)
"""
All the logic to convert a list of components into the rows and columns used to create the BoM.
"""
import locale
from copy import deepcopy
from math import ceil
from .units import compare_values, comp_match, get_last_warning
from .bom_writer import write_bom
from .columnlist import ColumnList
from ..misc import DNF, W_FIELDCONF, W_BADVAL1
from .. import log

logger = log.get_logger(__name__)
# RV == Resistor Variable or Varistor
# RN == Resistor 'N'(Pack)
# RT == Thermistor
RLC_PREFIX = {'R', 'L', 'C', 'RV', 'RN', 'RT'}


def compare_value(c1, c2, cfg):
    """ Compare the value of two components """
    c1_value = c1.value.strip().lower()
    c2_value = c2.value.strip().lower()
    # '~' is the same as empty for KiCad
    if c1_value == '~':
        c1_value = ''
    if c2_value == '~':
        c2_value = ''
    # Simple string comparison
    if c1_value == c2_value:
        return True
    # Otherwise, perform a more complicated value comparison
    if compare_values(c1, c2):
        return True
    # Ignore value if both components are connectors
    # Note: Is common practice to use the "Value" field of connectors to denote its use.
    #       In this case the values won't match even when the connectors are equivalent.
    if cfg.group_connectors:
        if 'connector' in c1.lib.lower() and 'connector' in c2.lib.lower():
            return True
    # No match, return False
    return False


def compare_part_name(c1, c2, cfg):
    """ Determine if two parts have the same name, compute aliases """
    pn1 = c1.name.lower()
    pn2 = c2.name.lower()
    # Simple direct match
    if pn1 == pn2:
        return True
    # Compare part aliases e.g. "c" to "c_small"
    for alias in cfg.component_aliases:
        if pn1 in alias and pn2 in alias:
            return True
    return False


def compare_field(c1, c2, field, cfg):
    c1_value = c1.get_field_value(field).lower()
    c2_value = c2.get_field_value(field).lower()
    # If blank comparisons are allowed
    if (c1_value == "" or c2_value == "") and cfg.merge_blank_fields:
        return True
    if not cfg.merge_both_blank and c1_value == "" and c2_value == "":
        # Avoid merging two components with empty field
        return False
    return c1_value == c2_value


def compare_components(c1, c2, cfg):
    """ Determine if two parts are 'equal' """
    # 'fitted' value must be the same for both parts
    if c1.fitted != c2.fitted:
        return False
    # 'fixed' value must be the same for both parts
    if c1.fixed != c2.fixed:
        return False
    # Do not group components
    if len(cfg.group_fields) == 0:
        return c1.ref == c2.ref
    # Check if the grouping fields match
    for i, field in enumerate(cfg.group_fields):
        # Check if we have a fallback
        field_alt = cfg.group_fields_fallbacks[i]
        if field_alt is not None:
            # Check if we have an empty field
            c1_value = c1.get_field_value(field)
            c2_value = c2.get_field_value(field)
            if c1_value == "" or c2_value == "":
                # Try with the fallback field
                c1_value = c1.get_field_value(field_alt)
                c2_value = c2.get_field_value(field_alt)
                if c1_value != "" and c2_value != "":
                    # Compare using the fallback
                    field = field_alt
        # Perform special matches
        if field == ColumnList.COL_VALUE_L:
            if not compare_value(c1, c2, cfg):
                return False
        # Match part name
        elif field == ColumnList.COL_PART_L:
            if not compare_part_name(c1, c2, cfg):
                return False
        # Generic match
        elif not compare_field(c1, c2, field, cfg):
            return False
    return True


class Joiner:
    def __init__(self):
        self.stack = {}

    def add(self, P, N):
        if P not in self.stack:
            self.stack[P] = [((P, N), (P, N))]
            return
        stack = self.stack[P]
        S, E = stack[-1]
        if N == E[1] + 1:
            stack[-1] = (S, (P, N))
        else:
            stack.append(((P, N), (P, N)))

    def flush(self, sep, dash='-'):
        refstr = u''
        c = 0
        for pref in sorted(self.stack.keys()):
            stack = self.stack[pref]
            for Q in stack:
                if c != 0:
                    refstr += sep
                S, E = Q
                refstr += S[0]+str(S[1])
                if S == E:
                    # Only one element
                    c += 1
                elif S[1]+1 == E[1]:
                    # Two elements, I think this is better than pretending this is a real range
                    refstr += sep+E[0]+str(E[1])
                    c += 2
                else:
                    # A range
                    refstr += dash+E[0]+str(E[1])
                    c += 2
        return refstr


def _suffix_to_num(suffix):
    return 0 if suffix == '?' else int(suffix)


class ComponentGroup(object):
    """ A row in the BoM """
    def __init__(self, cfg):
        """ Initialize the group with no components, and default fields """
        self.components = []
        self.refs = {}
        self.cfg = cfg
        # Columns loaded from KiCad
        self.fields = {c.lower(): None for c in ColumnList.COLUMNS_DEFAULT}
        self.field_names = deepcopy(ColumnList.COLUMNS_DEFAULT)

    def match_component(self, c):
        """ Test if a given component fits in this group """
        return compare_components(c, self.components[0], self.cfg)

    def contains_component(self, c):
        """ Test if a given component is already contained in this group """
        return c.ref+c.project in self.refs

    def add_component(self, c):
        """ Add a component to the group.
            Avoid repetition, checks if suitable.
            Note: repeated components happend when a component contains more than one unit """
        if not self.components:
            self.components.append(c)
            self.refs[c.ref+c.project] = c
        elif self.contains_component(c):
            return
        elif self.match_component(c):
            self.components.append(c)
            self.refs[c.ref+c.project] = c

    def round_qty(self, qty):
        if self.cfg.int_qtys:
            return int(ceil(qty))
        int_qty = int(qty)
        return int_qty if int_qty == qty else qty

    def get_count(self, project=None):
        if project is None:
            # Total components
            qty = sum(map(lambda c: c.qty, self.components))
        else:
            # Only for the specified project
            qty = sum(map(lambda c: c.qty if c.project == project else 0, self.components))
        return self.round_qty(qty)

    def get_build_count(self):
        if not self.is_fitted():
            # Not fitted -> 0
            return 0
        if len(self.cfg.aggregate) == 1:
            # Just one project
            qty = sum(map(lambda c: c.qty, self.components))*self.cfg.number
        else:
            # Multiple projects, count them using the number of board for each project
            qty = sum(map(lambda c: self.cfg.qtys[c.project]*c.qty, self.components))
        return self.round_qty(qty)

    def get_sources(self):
        sources = {}
        for c in self.components:
            prj = c.project
            if self.cfg.source_by_id:
                prj = self.cfg.source_to_id[prj]
            if prj in sources:
                sources[prj] += c.qty
            else:
                sources[prj] = c.qty
        field = ''
        for prj in sorted(sources.keys()):
            n = sources[prj]
            if len(field):
                field += ' '
            field += prj+'('+str(n)+')'
        return field

    def is_fitted(self):
        # compare_components ensures all has the same status
        return self.components[0].fitted

    def is_fixed(self):
        # compare_components ensures all has the same status
        return self.components[0].fixed

    def get_field(self, field):
        field = field.lower()
        if field not in self.fields or not self.fields[field]:
            return ""
        return self.fields[field]

    def sort_components(self):
        """ Sort the components in correct order (by reference).
            First priority is the prefix, second the number (as integer) """
        self.components = sorted(self.components, key=lambda c: [c.ref_prefix, _suffix_to_num(c.ref_suffix)])

    def get_refs(self):
        """ Return a list of the components """
        return self.cfg.ref_separator.join([c.ref for c in self.components])

    def get_alt_refs(self):
        """ Alternative list of references using ranges """
        refs = ''
        for sch in self.cfg.aggregate:
            S = Joiner()
            for n in self.components:
                if n.project == sch.name:
                    S.add(n.ref_id+n.ref_prefix, _suffix_to_num(n.ref_suffix))
            result = S.flush(self.cfg.ref_separator)
            if result:
                if refs:
                    refs += self.cfg.ref_separator
                refs += result
        return refs

    def update_field(self, field, value, ref=None):
        """ Update a given field, concatenates existing values and informs a collision """
        if not value:
            return
        field_ori = field
        field = field.lower()
        if (field not in self.fields) or (not self.fields[field]):
            self.fields[field] = value
            self.field_names.append(field_ori)
        elif value.lower() in self.fields[field].lower():
            return
        else:
            # Config contains variant information, which is different for each component
            # Part can be one of the defined aliases
            if field not in self.cfg.no_conflict:
                logger.warning(W_FIELDCONF + "Field conflict: ({refs}) [{name}] : '{flds}' <- '{fld}' (in {ref})".format(
                    refs=self.get_refs(),
                    name=field,
                    flds=self.fields[field],
                    fld=value, ref=ref))
            self.fields[field] += " " + value

    def update_fields(self, usealt=False):
        for c in self.components:
            for f, v in c.get_user_fields():
                self.update_field(f, v, c.ref)
        # Update 'global' fields
        if usealt:
            self.fields[ColumnList.COL_REFERENCE_L] = self.get_alt_refs()
        else:
            self.fields[ColumnList.COL_REFERENCE_L] = self.get_refs()
        # Quantity
        self.fields[ColumnList.COL_GRP_QUANTITY_L] = str(self.get_count())
        self.total = self.get_build_count()
        self.fields[ColumnList.COL_GRP_BUILD_QUANTITY_L] = str(self.total)
        self.fields[ColumnList.COL_SOURCE_BOM_L] = self.get_sources()
        # Group status
        status = ' '
        if not self.is_fitted():
            status += '(DNF)'
        if self.is_fixed():
            status += '(DNC)'
        self.fields[ColumnList.COL_STATUS_L] = status
        # Component data
        comp = self.components[0]
        self.fields[ColumnList.COL_VALUE_L] = comp.value
        self.fields[ColumnList.COL_PART_L] = comp.name
        self.fields[ColumnList.COL_PART_LIB_L] = comp.lib
        self.fields[ColumnList.COL_DATASHEET_L] = comp.datasheet
        self.fields[ColumnList.COL_FP_L] = comp.footprint
        self.fields[ColumnList.COL_FP_LIB_L] = comp.footprint_lib
        self.fields[ColumnList.COL_SHEETPATH_L] = comp.sheet_path_h
        if not self.fields[ColumnList.COL_DESCRIPTION_L]:
            self.fields[ColumnList.COL_DESCRIPTION_L] = comp.desc

    def get_row(self, columns):
        """ Return a dict of the KiCad data based on the supplied columns """
        row = []
        for key in columns:
            val = self.get_field(key)
            # Join fields (appending to current value)
            for join_l in self.cfg.join:
                # Each list is "target, source..." so we need at least 2 elements
                elements = len(join_l)
                target = join_l[0]
                if elements > 1 and target == key:
                    # Append data from the other fields
                    for source in join_l[1:]:
                        v = self.get_field(source)
                        if v:
                            val = val + ' ' + v
            row.append(val)
        return row


def get_value_sort(comp):
    """ Try to better sort R, L and C components """
    res = comp.value_sort
    if res:
        value, (mult, mult_s), unit = res
        if comp.ref_prefix in "CL":
            # fempto Farads
            value = "{0:15d}".format(int(value * 1e15 * mult + 0.1))
        else:
            # milli Ohms
            value = "{0:15d}".format(int(value * 1000 * mult + 0.1))
        return value
    return comp.value


def normalize_value(c, decimal_point):
    if c.value_sort is None:
        return c.value
    value, (mult, mult_s), unit = c.value_sort
    ivalue = int(value)
    if value == ivalue:
        value = ivalue
    elif decimal_point:
        value = str(value).replace('.', decimal_point)
    return '{} {}{}'.format(value, mult_s, unit)


def compute_multiple_stats(cfg, groups):
    for sch in cfg.aggregate:
        sch.comp_total = 0
        sch.comp_fitted = 0
        sch.comp_build = 0
        sch.comp_groups = 0
        for g in groups:
            g_l = g.get_count(sch.name)
            if g_l:
                sch.comp_groups = sch.comp_groups+1
            sch.comp_total += g_l
            if g.is_fitted():
                sch.comp_fitted += g_l
        sch.comp_build = sch.comp_fitted*sch.number
        if cfg.debug_level > 1:
            logger.debug('Stats for {}: total {} fitted {} build {}'.
                         format(sch.name, sch.comp_total, sch.comp_fitted, sch.comp_build))


def group_components(cfg, components):
    groups = []
    # Iterate through each component, and test whether a group for these already exists
    for c in components:
        if not c.included:  # Skip components marked as excluded from BoM
            continue
        # Cache the value used to sort
        if c.ref_prefix in RLC_PREFIX and c.value.lower() not in DNF:
            c.value_sort = comp_match(c.value, c.ref_prefix, c.ref)
            if c.value_sort is None and (' ' in c.value):
                # Try with the data before a space
                value = c.value.split(' ')[0]
                value_sort = comp_match(value, c.ref_prefix)
                if value_sort is not None:
                    c.value_sort = value_sort
                    logger.warning(get_last_warning() + "Using `{}` for {} instead".format(value, c.ref))
        else:
            c.value_sort = None
        # Try to add the component to an existing group
        found = False
        for g in groups:
            if g.match_component(c):
                g.add_component(c)
                found = True
                break
        if not found:
            # Create a new group
            g = ComponentGroup(cfg)
            g.add_component(c)
            groups.append(g)
    # Now unify the data from the components of each group
    decimal_point = None
    if cfg.normalize_locale:
        decimal_point = locale.localeconv()['decimal_point']
        if decimal_point == '.':
            decimal_point = None
    for g in groups:
        # Sort the references within each group
        g.sort_components()
        # Fill the columns
        g.update_fields(cfg.use_alt)
        if cfg.normalize_values:
            g.fields[ColumnList.COL_VALUE_L] = normalize_value(g.components[0], decimal_point)
    # Sort the groups
    # First priority is the Type of component (e.g. R?, U?, L?)
    groups = sorted(groups, key=lambda g: [g.components[0].ref_prefix, get_value_sort(g.components[0])])
    # Enumerate the groups and compute stats
    n_total = 0
    n_fitted = 0
    n_build = 0
    c = 1
    dnf = 1
    cfg.n_groups = len(groups)
    for g in groups:
        is_fitted = g.is_fitted()
        if cfg.ignore_dnf and not is_fitted:
            g.update_field('Row', str(dnf))
            dnf += 1
        else:
            g.update_field('Row', str(c))
            c += 1
        # Stats
        g_l = g.get_count()
        n_total += g_l
        if is_fitted:
            n_fitted += g_l
            n_build += g.total
    cfg.n_total = n_total
    cfg.n_fitted = n_fitted
    cfg.n_build = n_build
    if cfg.debug_level > 1:
        logger.debug('Global stats: total {} fitted {} build {}'.format(n_total, n_fitted, n_build))
    # Compute stats for multiple schematics
    if len(cfg.aggregate) > 1:
        compute_multiple_stats(cfg, groups)
    return groups


def do_bom(file_name, ext, comps, cfg):
    # Group components according to group_fields
    groups = group_components(cfg, comps)
    # Create the BoM
    logger.debug("Saving BOM File: "+file_name)
    number = cfg.number
    cfg.number = sum(map(lambda prj: prj.number, cfg.aggregate))
    write_bom(file_name, ext, groups, cfg.columns, cfg)
    cfg.number = number
