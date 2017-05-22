# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from operator import attrgetter

from trytond import backend
from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, And, Bool
from trytond.transaction import Transaction
from sql.operators import In
from sql.aggregate import Max
from .aeat import (OPERATION_KEY, BOOK_KEY, SEND_SPECIAL_REGIME_KEY,
        RECEIVE_SPECIAL_REGIME_KEY, AEAT_INVOICE_STATE, IVA_SUBJECTED,
        EXCEMPTION_CAUSE, INTRACOMUNITARY_TYPE)

from .pyAEATsii import mapping

__all__ = ['Invoice', 'ReasignSIIRecord', 'ReasignSIIRecordStart',
    'ReasignSIIRecordEnd']


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    sii_book_key = fields.Selection([(None, ''), ] + BOOK_KEY,
        'SII Book Key')
    sii_operation_key = fields.Selection([(None, ''), ] + OPERATION_KEY,
        'SII Operation Key')
    sii_issued_key = fields.Selection([(None, ''),] + SEND_SPECIAL_REGIME_KEY,
        'SII Issued Key',
        states={
            'invisible': ~Eval('type').in_(['out_invoice', 'out_credit_note']),
        })
    sii_received_key = fields.Selection([(None, ''),] +
        RECEIVE_SPECIAL_REGIME_KEY, 'SII Recived Key',
        states={
            'invisible': Eval('type').in_(['out_invoice', 'out_credit_note']),
        })
    sii_subjected = fields.Selection([(None, '')]+ IVA_SUBJECTED, 'Subjected')
    sii_excemtion_cause = fields.Selection([(None, '')] + EXCEMPTION_CAUSE,
        'Excemption Cause')
    sii_intracomunity_key = fields.Selection([(None, ''),] + INTRACOMUNITARY_TYPE,
        'SII Intracommunity Key',
        # TODO
        # states={
        #     'invisible': ~Eval('type').in_(['out_invoice', 'out_credit_note']),
        # }
        )


    sii_records = fields.One2Many('aeat.sii.report.lines', 'invoice',
        "Sii Report Lines")
    sii_state = fields.Function(fields.Selection(AEAT_INVOICE_STATE,
            'SII State'), 'get_sii_state', searcher='search_sii_state')


    @classmethod
    def search_sii_state(cls, name, clause):
        pool = Pool()
        SIILines = pool.get('aeat.sii.report.lines')

        table = SIILines.__table__()

        cursor = Transaction().cursor
        cursor.execute(*table.select(Max(table.id), table.invoice,
            group_by=table.invoice))

        invoices = []
        lines = []
        for id_, invoice in cursor.fetchall():
            invoices.append(invoice)
            lines.append(id_)

        if clause[-1] == None:
            return [('id', 'not in', invoices)]

        clause2 = [tuple(('state',)) + tuple(clause[1:])] + \
            [('id', 'in', lines)]

        print "clause2:", clause2

        res_lines = SIILines.search(clause2)
        return [('id', 'in', [x.invoice.id for x in res_lines])]



    @classmethod
    def get_sii_state(cls, invoices, names):
        pool = Pool()
        SIILines = pool.get('aeat.sii.report.lines')
        result = {}
        for name in names:
            result[name] = dict((i.id, '') for i in invoices)

        table = SIILines.__table__()
        cursor = Transaction().cursor
        cursor.execute(*table.select(Max(table.id), table.invoice,
            where=table.invoice.in_([x.id for x in invoices]),
            group_by=table.invoice))

        lines = [a[0] for a in cursor.fetchall()]

        if lines:
            cursor.execute(*table.select(table.state, table.invoice,
                where=table.id.in_(lines)))

            for state, inv in cursor.fetchall():
                result['sii_state'][inv] = state

        return result

    @classmethod
    def map_to_aeat_sii(cls, invoices):
        mapper = IssuedTrytonInvoiceMapper()
        return map(mapper.build_request, invoices)


class IssuedTrytonInvoiceMapper(mapping.OutInvoiceMapper):
    year = attrgetter('move.period.fiscalyear.name')
    period = attrgetter('move.period.start_date.month')
    nif = attrgetter('company.party.vat_number')
    serial_number = attrgetter('number')
    issue_date = attrgetter('invoice_date')
    invoice_kind = attrgetter('sii_operation_key')
    specialkey_or_trascendence = attrgetter('sii_issued_key')
    description = attrgetter('description')
    not_exempt_kind = attrgetter('sii_subjected')
    counterpart_name = attrgetter('party.name')
    counterpart_nif = attrgetter('party.vat_number')
    counterpart_id_type = attrgetter('party.identifier_type')
    counterpart_country = attrgetter('party.vat_country')
    taxes = attrgetter('taxes')
    tax_rate = attrgetter('tax.rate')
    tax_base = attrgetter('base')
    tax_amount = attrgetter('amount')


class ReasignSIIRecordStart(ModelView):
    """
    Reasign AEAT SII Records Start
    """
    __name__ = "aeat.sii.reasign.records.start"

    book_key = fields.Selection(BOOK_KEY, 'Book Key', sort=False)
    operation_key = fields.Selection(OPERATION_KEY, 'Operation Key', sort=False)


class ReasignSIIRecordEnd(ModelView):
    """
    Reasign AEAT SII Records End
    """
    __name__ = "aeat.sii.reasign.records.end"


class ReasignSIIRecord(Wizard):
    """
    Reasign AEAT SII Records
    """
    __name__ = "aeat.sii.reasign.records"
    start = StateView('aeat.sii.reasign.records.start',
        'aeat_sii.aeat_sii_reasign_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Reasign', 'reasign', 'tryton-ok', default=True),
            ])
    reasign = StateTransition()
    done = StateView('aeat.sii.reasign.records.end',
        'aeat_sii.aeat_sii_reasign_end_view', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])

    @classmethod
    def __setup__(cls):
        super(ReasignSIIRecord, cls).__setup__()
        cls._error_messages.update({
                'sii_book_key_not_available': (
                    'The AEAT Sii Book Key "%s" is not available for any of '
                    'selected invoices.'),
                })

    def transition_reasign(self):
        Invoice = Pool().get('account.invoice')
        Line = Pool().get('account.invoice.line')
        cursor = Transaction().cursor
        invoices = Invoice.browse(Transaction().context['active_ids'])

        invoice = Invoice.__table__()

        value = self.start.book_key
        value2 = self.start.operation_key
        # Update to allow to modify key for posted invoices
        cursor.execute(*invoice.update(columns=[invoice.sii_book_key,
            invoice.sii_operation_key],
            values=[value, value2], where=In(invoice.id,
                [x.id for x in invoices])))

        # invoices = Invoice.browse(invoices)
        # Invoice.create_aeat340_records(invoices)

        return 'done'
