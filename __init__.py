# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

from . import invoice
from . import aeat
from . import party

def register():
    Pool.register(
        party.Party,
        invoice.Invoice,
        invoice.ReasignSIIRecordStart,
        invoice.ReasignSIIRecordEnd,
        aeat.SIIReport,
        aeat.SIIReportLine,
        module='aeat_sii', type_='model')
    Pool.register(
        invoice.ReasignSIIRecord,
        module='aeat_sii', type_='wizard')
