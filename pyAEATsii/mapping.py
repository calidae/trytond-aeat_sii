
__all__ = [
    'get_headers',
    'OutInvoiceMapper',
]


def get_headers(name=None, vat=None, comm_kind=None, version='0.7'):
    return {
        'IDVersionSii': version,
        'Titular': {
            'NombreRazon': name,
            'NIF': vat,
        },
        'TipoComunicacion': comm_kind,
    }


class OutInvoiceMapper(object):

    @classmethod
    def build_request(cls, invoice):
        return {
            'PeriodoImpositivo': cls.build_period(invoice),
            'IDFactura': cls.build_invoice_id(invoice),
            'FacturaExpedida': cls.build_issued_invoice(invoice),
        }

    @classmethod
    def build_period(cls, invoice):
        return {
            'Ejercicio': cls.year(invoice),
            'Periodo': str(cls.period(invoice)).zfill(2),
        }

    @classmethod
    def build_invoice_id(cls, invoice):
        return {
            'IDEmisorFactura': {
                'NIF': cls.nif(invoice),
            },
            'NumSerieFacturaEmisor': cls.serial_number(invoice),
            'FechaExpedicionFacturaEmisor':
                cls.issue_date(invoice).strftime('%d/%m/%Y'),
        }

    @classmethod
    def build_issued_invoice(cls, invoice):
        ret = {
            'TipoFactura': cls.invoice_kind(invoice),
            'ClaveRegimenEspecialOTrascendencia':
                cls.specialkey_or_trascendence(invoice),
            'DescripcionOperacion': cls.description(invoice),
            'TipoDesglose': {
                'DesgloseFactura': {
                    'Sujeta': {
                        # 'Exenta': {
                        #     'CausaExcencion': E1-E6
                        #     'BaseImponible': '0.00',
                        # },
                        'NoExenta': {
                            'TipoNoExenta': cls.not_exempt_kind(invoice),
                            'DesgloseIVA': {
                                'DetalleIVA':
                                    map(cls.build_taxes, cls.taxes(invoice)),
                            }
                        },
                    },
                    # 'NoSujeta': {
                    #     'ImportePorArticulos7_14_Otros': 0,
                    #     'ImporteTAIReglasLocalizacion': 0,
                    # },
                },
                # 'DesgloseTipoOperacion': {
                #     'PrestacionDeServicios':
                #         {'Sujeta': {'Exenta': {}, 'NoExenta': {}}, 'NoSujeta': {}},
                #     'Entrega':
                #         {'Sujeta': {'Exenta': {}, 'NoExenta': {}}, 'NoSujeta': {}},
                # },
            },
        }
        if ret['TipoFactura'] not in {'F2', 'F4', 'R5'}:
            ret['Contraparte'] = cls.build_counterpart(invoice)
        return ret

    @classmethod
    def build_counterpart(cls, invoice):
        return {
            'NombreRazon': cls.counterpart_name(invoice),
            # 'NIF': cls.counterpart_nif(invoice),
            'IDOtro': {
                'IDType': cls.counterpart_id_type(invoice),
                'CodigoPais': cls.counterpart_country(invoice),
                'ID': cls.counterpart_nif(invoice),
            },
        }

    @classmethod
    def build_taxes(cls, tax):
        return {
            'TipoImpositivo': int(100 * cls.tax_rate(tax)),
            'BaseImponible': cls.tax_base(tax),
            'CuotaRepercutida': cls.tax_amount(tax),
            # TODO: TipoRecargoEquivalencia, CuotaRecargoEquivalencia
        }
