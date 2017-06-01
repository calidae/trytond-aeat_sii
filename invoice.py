# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

from sql.aggregate import Max
from .aeat import (
    OPERATION_KEY, BOOK_KEY, SEND_SPECIAL_REGIME_KEY,
    RECEIVE_SPECIAL_REGIME_KEY, AEAT_INVOICE_STATE, IVA_SUBJECTED,
    EXCEMPTION_CAUSE, INTRACOMUNITARY_TYPE)


__all__ = ['Invoice']


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    sii_book_key = fields.Selection([(None, ''), ] + BOOK_KEY,
        'SII Book Key')
    sii_operation_key = fields.Selection([(None, ''), ] + OPERATION_KEY,
        'SII Operation Key')
    sii_issued_key = fields.Selection([(None, ''), ] + SEND_SPECIAL_REGIME_KEY,
        'SII Issued Key',
        states={
            'invisible': ~Eval('type').in_(['out_invoice', 'out_credit_note']),
        })
    sii_received_key = fields.Selection([(None, ''), ] +
        RECEIVE_SPECIAL_REGIME_KEY, 'SII Recived Key',
        states={
            'invisible': Eval('type').in_(['out_invoice', 'out_credit_note']),
        })
    sii_subjected = fields.Selection([(None, '')] + IVA_SUBJECTED, 'Subjected')
    sii_excemption_cause = fields.Selection([(None, '')] + EXCEMPTION_CAUSE,
        'Excemption Cause')
    sii_intracomunity_key = fields.Selection([(None, ''), ] +
        INTRACOMUNITARY_TYPE, 'SII Intracommunity Key',
        states={
            'invisible': ~Eval('sii_book_key').in_(['U']),
        }
    )
    sii_records = fields.One2Many('aeat.sii.report.lines', 'invoice',
        "Sii Report Lines")
    sii_state = fields.Function(fields.Selection(AEAT_INVOICE_STATE,
            'SII State'), 'get_sii_state', searcher='search_sii_state')

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._check_modify_exclude += ['sii_book_key', 'sii_operation_key',
            'sii_received_key', 'sii_issued_key', 'sii_subjected',
            'sii_excemption_cause', 'sii_intracomunity_key']

    @staticmethod
    def default_sii_book_key():
        type_ = Transaction().context.get('type', 'out_invoice')
        book_key = 'E'
        if type_ and type_ == 'in_invoice':
            book_key = 'R'

        return book_key

    @staticmethod
    def default_sii_subjected():
        return 'S1'

    @staticmethod
    def default_sii_issued_key():
        type_ = Transaction().context.get('type', 'out_invoice')
        if type_ == 'out_invoice':
            return '01'
        return 'None'

    @staticmethod
    def default_sii_received_key():
        type_ = Transaction().context.get('type', 'out_invoice')
        if type_ == 'in_invoice':
            return '01'
        return 'None'

    @staticmethod
    def default_sii_operation_key():
        type_ = Transaction().context.get('type', 'out_invoice')
        if type_ in ('in_credit_note', 'out_credit_note'):
            return 'R1'
        return 'F1'

    @classmethod
    def search_sii_state(cls, name, clause):
        pool = Pool()
        SIILines = pool.get('aeat.sii.report.lines')

        table = SIILines.__table__()

        cursor = Transaction().connection.cursor()
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
        cursor = Transaction().connection.cursor()
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

    def _credit(self):
        res = super(Invoice, self)._credit()
        for field in ('sii_book_key', 'sii_issued_key', 'sii_received_key',
                'sii_subjected', 'sii_excemption_cause',
                'sii_intracomunity_key'):
            res[field] = getattr(self, field)

        res['sii_operation_key'] = 'R4'
        return res
