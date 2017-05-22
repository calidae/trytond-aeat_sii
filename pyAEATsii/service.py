
__all__ = [
    'bind_SuministroFactEmitidas',
]

from requests import Session

from zeep import Client
from zeep.transports import Transport
from zeep.plugins import HistoryPlugin

from .plugins import LoggingPlugin


def _get_client(wsdl, public_crt, private_key, test=False):
    session = Session()
    session.cert = (public_crt, private_key)
    transport = Transport(session=session)
    plugins = [HistoryPlugin()]
    # TODO: manually handle sessionId? Not mandatory yet recommended...
    # http://www.agenciatributaria.es/AEAT.internet/Inicio/Ayuda/Modelos__Procedimientos_y_Servicios/Ayuda_P_G417____IVA__Llevanza_de_libros_registro__SII_/Ayuda_tecnica/Informacion_tecnica_SII/Preguntas_tecnicas_frecuentes/1__Cuestiones_Generales/16___Como_se_debe_utilizar_el_dato_sesionId__.shtml
    if test:
        plugins.append(LoggingPlugin())
    client = Client(wsdl=wsdl, transport=transport, plugins=plugins)
    return client


def bind_SuministroFactEmitidas(crt, pkey, test=False):
    wsdl = (
        'http://www.agenciatributaria.es/static_files/AEAT/'
        'Contenidos_Comunes/La_Agencia_Tributaria/Modelos_y_formularios/'
        'Suministro_inmediato_informacion/FicherosSuministros/V_07/'
        'SuministroFactEmitidas.wsdl'
    )
    port_name = 'SuministroFactEmitidas'
    if test:
        port_name += 'Pruebas'
    cli = _get_client(wsdl, crt, pkey, test)
    service = cli.bind('siiService', port_name)
    return service

    # wsdl_in = fields.Char(
    #     string='WSDL Invoice In', required=True,
    #     default='http://www.agenciatributaria.es/static_files/AEAT/'
    #     'Contenidos_Comunes/La_Agencia_Tributaria/Modelos_y_formularios/'
    #     'Suministro_inmediato_informacion/FicherosSuministros/V_06/'
    #     'SuministroFactRecibidas.wsdl')
