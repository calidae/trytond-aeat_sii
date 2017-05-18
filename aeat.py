# -*- coding: utf-8 -*-
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unicodedata
from logging import getLogger
from decimal import Decimal
from trytond.model import ModelSQL, ModelView, fields, Workflow
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from . import aeat_errors

__all__ = ['SIIReport', 'SIIReportLine']
_logger = getLogger(__name__)
_ZERO = Decimal('0.0')

COMMUNICATION_TYPE = [   # L0
    ('A0', 'New Invoices'),
    ('A1', 'Modify Invoices'),
    ('A4', 'Modify (Travelers)'),
    ('C0', 'Query Invoices'), # Not in L0
    ('D0', 'Delete Invoices'), # Not In L0

]

BOOK_KEY = [
    ('E', 'Issued Invoices'),
    ('I', 'Investment Goods'),
    ('R', 'Received Invoices'),
    ('U', 'Particular Intracommunity Operations'),
    ('F', 'IGIC Issued Invoices'),
    ('J', 'IGIC Investment Goods'),
    ('S', 'IGIC Received Invoices'),
    ]

OPERATION_KEY = [    # L2_EMI - L2_RECI
    ('F1', 'Invoice'),
    ('F2', 'Simplified Invoice'),
    ('R1', 'Credit Note (Art 80.1 y 80.2)'),
    ('R2', 'Credit Note (Art 80.3)'),
    ('R3', 'Credit Note (Art 80.4)'),
    ('R4', 'Credit Note'),
    ('R5', 'Credit Note on simplified Invoices'),
    ('F3', 'Invoice issued as a substitute for simplified invoices'
        'Billed and declared'),
    ('F4', 'Invoice Summary Account Move'),
    ('F5', 'Import (DUA)'),
    ('F6', 'Other accounting documents'),

]

PARTY_IDENTIFIER_TYPE = [
    ('02', 'NIF'),
    ('03', 'Passport'),
    ('04', 'Official Document Emmited by the Country of Residence'),
    ('05', 'Certificate of fiscal resident'),
    ('06', 'Other proving document'),
    ]


SEND_SPECIAL_REGIME_KEY = [  # L3.1
    ('01', 'Common System Operation'),
    ('02', 'Export'),
    ('03', 'Operations to which the special arrangements for second-hand goods,'
        ' art objects, antiques and collectors articles apply (135-139 LIVA)'),
    ('04', 'Special investment gold regime'),
    ('05', 'Special travel agencies'),
    ('06', 'Special group of entities in VAT (Advanced Level)'),
    ('07', 'Special scheme for cash'),
    ('08', 'Operations subject to IPSI / IGIC'),
    ('09', 'Invoicing of travel agency services acting as mediators in the '
           'name and for the account of others (D.A.4a RD1619 2012)'),
#     ('10', 'Collection on behalf of third parties of professional fees or '
#         'rights derived from industrial property, author or others...'),
#      ('11', 'Business premises lease transactions subject to withholding'),
#     ('12', 'Non-retention business lease operations'),
#     ('13', 'Lease transactions of business premises subject to and not subject '
#         ' to withholding'),
#     ('14', 'Invoice with tax pending of accrual (certifications of works whose'
#         ' addressee is a Public Administration)'),
#     ('15', 'Invoice with VAT pending accrual - operations of successive tract'),
    ]

RECEIVE_SPECIAL_REGIME_KEY = [
    ('01', 'Common system operation'),
    ('02', 'Operations by which employers satisfy REAGYP compensation'),
    ('03', 'Operations to which the special arrangements for second-hand goods,'
        ' art objects, antiques and collectors articles apply (135-139 LIVA)'),
    ('04', 'Special investment gold regime'),
    ('05', 'Special travel agencies'),
    ('06', 'Special group of entities in VAT (Advanced Level)'),
    ('07', 'Special scheme for cash'),
    ('08', 'Operations subject to IPSI / IGIC'),
    ('09', 'Intra-Community acquisitions of goods and services'),
    ('10', 'Purchase of travel agencies: mediation operations in the name and '
        'for the account of others in transport services provided to the '
        'recipient of the services in accordance with section 3 '
        'of D.A.4a RD1619 / 2012'),
    ('11', 'Billing of travel agency services acting as mediators in the name '
        'and for the account of others (D.A.4a RD1619 / 2012)'),
    ('12', 'Business premises lease operations'),
    ('13', 'Invoice corresponding to an import '
        '(reported without associating with a DUA)')
]

AEAT_COMMUNICATION_STATE = [
    (None, ''),
    ('CORRECTO', 'Accepted'),
    ('PARCIALMENTECORRECTO', 'Partial Accepted'),
    ('INCORRECTO', 'Rejected')
]

AEAT_INVOICE_STATE = [
    (None, ''),
    ('CORRECTO', 'Accepted'),
    ('ACEPTADOCONERRORES', 'Accepted with Errors'),
    ('INCORRECTO', 'Rejected')
]


PROPERTY_STATE = [  # L6
    ('0', ''),
    ('1',
        '1. Property with cadastral reference located at any point in the '
        'Spanish territory, except the Basque Country and Navarra.'),
    ('2',
        '2. Property located in the Autonomous Community of the Basque '
        'Country or in the Comunidad Foral de Navarra.'),
    ('3',
        '3. Property in any of the above situations but without cadastral '
        'reference.'),
    ('4', '4. Property located in the foreign country.'),
    ]


# L7 - Iva Subjected
IVA_SUBJECTED = [
    ('S1', 'Subjected - Not Excempt'),
    ('S2', 'Subjected - Not Excempt ,  Inv. Suj. Pass')
]

# L9 - Excemption cause
EXCEMPTION_CAUSE = [
    ('E1', 'Excempt. Article 20'),
    ('E2', 'Excempt. Article 21'),
    ('E3', 'Excempt. Article 22'),
    ('E4', 'Excempt. Article 24'),
    ('E5', 'Excempt. Article 25'),
    ('E6', 'Excempt. Other'),
]

# L11 Payment Type
PAYMENT_TYPE = [
    ('01', 'Transference'),
    ('02', 'Check'),
    ('03', 'Not Paid (ERE)'),
    ('04', 'Other')
]

# L12
INTRACOMUNITARY_TYPE = [
    ('A', 'The sending or receiving of goods for the execution of the partial\n'
           'reports or works Mentioned in article 70, paragraph one, number 7,\n'
           'of the Tax Law (Law 37/1992).'),
    ('B', 'Transfers of goods and intra-Community acquisitions of goods \n'
          'covered by In articles 9, paragraph 3, and 16, section 2, of the \n'
          'Tax Law (Law 37/1992).'),
]


def remove_accents(unicode_string):
    if isinstance(unicode_string, str):
        unicode_string_bak = unicode_string
        try:
            unicode_string = unicode_string_bak.decode('iso-8859-1')
        except UnicodeDecodeError:
            try:
                unicode_string = unicode_string_bak.decode('utf-8')
            except UnicodeDecodeError:
                return unicode_string_bak

    if not isinstance(unicode_string, unicode):
        return unicode_string

    # From http://www.leccionespracticas.com/uncategorized/eliminar-tildes-con-python-solucionado
    unicode_string_nfd = ''.join(
        (c for c in unicodedata.normalize('NFD', unicode_string)
            if (unicodedata.category(c) != 'Mn'
                or c in (u'\u0327', u'\u0303'))  # ç or ñ
            ))
    # It converts nfd to nfc to allow unicode.decode()
    return unicodedata.normalize('NFC', unicode_string_nfd)

_STATES = {
    'readonly': Eval('state') != 'draft',
    }
_DEPENDS = ['state']


class SIIReport(Workflow, ModelSQL, ModelView):
    ''' SII Report '''
    __name__ = 'aeat.sii.report'

    company = fields.Many2One('company.company', 'Company', required=True,
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])
    currency = fields.Function(fields.Many2One('currency.currency',
        'Currency'), 'get_currency')
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True, states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])
    company_vat = fields.Char('VAT', size=9, states={
            'required': Eval('state').in_(['confirmed', 'done']),
            'readonly': ~Eval('state').in_(['draft', 'confirmed']),
            }, depends=['state'])

    period = fields.Many2One('account.period', 'Period', required=True,
        domain = [('fiscalyear','=', Eval('fiscalyear'))],
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])

    operation_type = fields.Selection(COMMUNICATION_TYPE, 'Operation Type',
        required=True,
        states={
            'readonly': ~Eval('state').in_(['draft', 'confirmed']),
            }, depends=['state'])

    book = fields.Selection(BOOK_KEY, 'Book', required=True,
        states={
            'readonly': ~Eval('state').in_(['draft', 'confirmed']),
            }, depends=['state'])

    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled')
            ], 'State', readonly=True)

    communication_state = fields.Selection( AEAT_COMMUNICATION_STATE,
        'Communication State', readonly=True)

    version = fields.Selection([
            ('0.6', '0.6'),
            ], 'Version', required=True, states={
                'readonly': ~Eval('state').in_(['draft', 'confirmed']),
                }, depends=['state'])

    lines = fields.One2Many('aeat.sii.report.lines', 'report',
        'Lines', states={
            'readonly': ~Eval('state').in_(['draft']),
            }, depends=['state'])


    @classmethod
    def __setup__(cls):
        super(SIIReport, cls).__setup__()
        cls._buttons.update({
                'draft': {
                    'invisible': ~Eval('state').in_(['confirmed',
                            'cancelled']),
                    'icon': 'tryton-go-previous',
                    },
                'confirm': {
                    'invisible': ~Eval('state').in_(['draft']),
                    'icon': 'tryton-go-next',
                    },
                'send': {
                    'invisible': ~Eval('state').in_(['confirmed']),
                    'icon': 'tryton-ok',
                    },
                'cancel': {
                    'invisible': Eval('state').in_(['cancelled']),
                    'icon': 'tryton-cancel',
                    },
                'load_invoices': {
                    'invisible': ~(Eval('state').in_(['draft']) &
                         Eval('operation_type').in_(['A0','A1'])),
                    }
                })

        cls._transitions |= set((
                ('draft', 'confirmed'),
                ('draft', 'cancelled'),
                ('confirmed', 'draft'),
                ('confirmed', 'sent'),
                ('confirmed', 'cancelled'),
                ('cancelled', 'draft'),
                ))



    @staticmethod
    def default_company():

        return Transaction().context.get('company')

    def get_currency(self, name):
        return self.company.currency.id

    @staticmethod
    def default_fiscalyear():
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(
            Transaction().context.get('company'), exception=False)

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_version():
        return '0.6'

    @fields.depends('company')
    def on_change_with_company_vat(self):
        if self.company:
            return self.company.party.vat_number

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, reports):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, reports):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('sent')
    def send(cls, reports):
        _logger.info(
            'Sending reports (%s) to AEAT SII',
            ','.join(str(r.id) for r in reports))
        for report in reports:
            with report.company.tmp_ssl_credentials() as (crt, key):
                raise NotImplementedError

    @classmethod
    @ModelView.button
    @Workflow.transition('cancelled')
    def cancel(cls, reports):
        pass

    @classmethod
    @ModelView.button
    def load_invoices(cls, reports):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        ReportLine = pool.get('aeat.sii.report.lines')

        for report in reports:
            domain = [
                ('sii_book_key', '=', report.book),
                ('move.period', '=', report.period.id),
                ('state', 'in', ['posted', 'paid']),
            ]

            if report.operation_type == 'A0':
                domain.append(('sii_state', '=', None))
            elif report.operation_type in ('A1', 'A4'):
                domain.append(('sii_state', 'in', [
                    'ACEPTADOCONERRORES', 'INCORRECTO']))

            _logger.debug('Searching invoices for SII report: %s', domain)
            invoices = Invoice.search(domain)
            report.lines = [
                ReportLine(invoice=invoice, report=report)
                for invoice in invoices
            ]
            report.save()


class SIIReportLine(ModelSQL, ModelView):
    '''
    AEAT SII Issued
    '''
    __name__ = 'aeat.sii.report.lines'

    report = fields.Many2One(
        'aeat.sii.report', 'Issued Report', ondelete='CASCADE')
    invoice = fields.Many2One('account.invoice', 'Invoice')
    state = fields.Selection(AEAT_INVOICE_STATE, 'State')
    communication_msg = fields.Selection(
        aeat_errors.AEAT_ERRORS, 'Communication Message', readonly=True)
    company = fields.Many2One(
        'company.company', 'Company', required=True, select=True)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')
