# -*- encoding: utf-8 -*-
##############################################################################

{
    "name": "Ventas y Cobros Veddepessa",
    "depends": [
        "base",
        "account",
        "purchase",
        "banks",
        "delivery_cost",
        "sale_margin",
        "invoice_discount"
    ],
    "author": "Alejandro Rodriguez, Honduras Opensource",
    "website": "http://www.hondurasopensource.com",
    "category": "Accounting",
    "description": """
        Ventas y Cobros Veddepessa.
    """,
    'data': [
        "data/report_format_paper.xml",
        "security/ir.model.access.csv",
        "wizard/wiz_create_invoice_view.xml",
        "views/account_treasury_forecast_view.xml",
        "views/cadena_suministro_view.xml",
        "views/report_cliente_view.xml",
        "reports/report_cashflow_detail.xml",
        "reports/report_cashflow_detail_view.xml",
        "views/descuento_sesenta_view.xml",
        "views/antiguedad_saldo_cliente.xml",
        "views/libro_ventas_view.xml",
        "views/cliente_galones.xml",
        "views/city_gallons.xml",
        "views/journal_entries_modified.xml",
        "views/liquidacion_60_grados.xml",
    ],
    'demo': [],
    'installable': True,
}
