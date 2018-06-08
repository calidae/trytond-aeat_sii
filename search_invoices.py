# -*- coding: utf-8 -*-
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from logging import getLogger

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pyson import Eval, If, Equal

from .aeat import BOOK_KEY, COMMUNICATION_TYPE

__all__ = [
    'StartView',
    'SearchInvoicesWizard',
]

_logger = getLogger(__name__)


# TODO: fix account.invoice `sii_state` searcher performance
# and uncomment all code blocks regarding `operation_type`

class StartView(ModelView):
    'Search Invoices Start View'
    __name__ = 'aeat.sii.search_invoices.start'

    company = fields.Many2One('company.company', 'Company')
    period = fields.Many2One('account.period', 'Period')
    book = fields.Selection(BOOK_KEY, 'Book')
    operation_type = fields.Selection(COMMUNICATION_TYPE, 'Operation Type')

    invoices = fields.Many2Many(
        'account.invoice', None, None, 'Invoices',
        domain=[
            If(
                Equal(Eval('book'), 'E'),  # issued
                ('type', 'in', ['out_invoice', 'out_credit_note']),
                If(
                    Equal(Eval('book'), 'R'),  # recieved
                    ('type', 'in', ['in_invoice', 'in_credit_note']),
                    ('id', '!=', None)  # dummy clause
                )
            ),
            ('state', 'in', ['posted', 'paid']),
            ('company', '=', Eval('company')),
            ('move.period', '=', Eval('period')),
            # If(
            #     Equal(Eval('operation_type'), 'A0'),  # create
            #     ('sii_state', 'in', [None, 'Incorrecto']),
            #     If(
            #         In(Eval('operation_type'), ['A1', 'D0']),  # edit/delete
            #         ('sii_state', 'in', [
            #             'Correcto', 'Correcta',
            #             'AceptadoConErrores', 'AceptadaConErrores']),
            #         ('id', '!=', None)  # dummy clause
            #     )
            # ),
        ],
        depends=[
            'company', 'period', 'book',  # 'operation_type',
        ],
    )


class SearchInvoicesWizard(Wizard):
    'Search Invoices Wizard'
    __name__ = 'aeat.sii.search_invoices.wizard'

    start = StateView(
        'aeat.sii.search_invoices.start',
        'aeat_sii.search_invoices_start_view_form',
        [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Attach', 'attach', 'tryton-ok', default=True),
        ]
    )
    attach = StateTransition()

    def default_start(self, fields):
        SIIReport = Pool().get('aeat.sii.report')
        sii_report = SIIReport(
            Transaction().context['active_id']
        )
        return {
            'company': sii_report.company.id,
            'period': sii_report.period.id,
            'book': sii_report.book,
            'operation_type': sii_report.operation_type,
        }

    def transition_attach(self):
        SIIReportLine = Pool().get('aeat.sii.report.lines')
        report_id = Transaction().context['active_id']
        SIIReportLine.create([
            {
                'report': report_id,
                'invoice': invoice.id,
            }
            for invoice in self.start.invoices
        ])
        return 'end'
