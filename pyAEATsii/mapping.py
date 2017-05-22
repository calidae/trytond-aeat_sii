
__all__ = [
    'get_headers',
    'OutInvoiceMapper',
]


def get_headers(name=None, vat=None, comm_kind=None, version='0.6'):
    return {
        'IDVersionSii': version,
        'Titular': {
            'NombreRazon': name,
            'NIF': vat,
        },
        'TipoComunicacion': comm_kind,
    }


class OutInvoiceMapper(object):
    def __init__(self):
        pass

    def build_request(self, invoice):
        return {
            'PeriodoImpositivo': self.build_period(invoice),
            'IDFactura': self.build_invoice_id(invoice),
            'FacturaExpedida': self.build_issued_invoice(invoice),
        }

    def build_period(self, invoice):
        return {
            'Ejercicio': self.year(invoice),
            'Periodo': str(self.period(invoice)).zfill(2),
        }

    def build_invoice_id(self, invoice):
        return {
            'IDEmisorFactura': {
                'NIF': self.nif(invoice),
            },
            'NumSerieFacturaEmisor': self.serial_number(invoice),
            'FechaExpedicionFacturaEmisor':
                self.issue_date(invoice).strftime('%d/%m/%Y'),
        }

    def build_issued_invoice(self, invoice):
        ret = {
            'TipoFactura': self.invoice_kind(invoice),
            'ClaveRegimenEspecialOTrascendencia':
                self.specialkey_or_trascendence(invoice),
            'DescripcionOperacion': self.description(invoice),
            'TipoDesglose': {
                'DesgloseFactura': {
                    'Sujeta': {
                        # 'Exenta': {
                        #     'BaseImponible': '0.00',
                        # },
                        'NoExenta': {
                            'TipoNoExenta': self.not_exempt_kind(invoice),
                            'DesgloseIVA': {
                                'DetalleIVA':
                                    map(self.build_taxes, self.taxes(invoice)),
                            }
                        },
                    },
                    # 'NoSujeta': {
                    # },
                },
            },
        }
        if ret['TipoFactura'] not in {'F2', 'F4', 'R5'}:
            ret['Contraparte'] = self.build_counterpart(invoice)
        return ret

    def build_counterpart(self, invoice):
        return {
            'NombreRazon': self.counterpart_name(invoice),
            # 'NIF': self.counterpart_nif(invoice),
            'IDOtro': {
                'IDType': self.counterpart_id_type(invoice),
                'CodigoPais': self.counterpart_country(invoice),
                'ID': self.counterpart_nif(invoice),
            },
        }

    def build_taxes(self, tax):
        return {
            'TipoImpositivo': int(100 * self.tax_rate(tax)),
            'BaseImponible': self.tax_base(tax),
            'CuotaRepercutida': self.tax_amount(tax),
        }
