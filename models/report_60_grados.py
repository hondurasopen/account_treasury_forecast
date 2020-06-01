# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import date,datetime


class DeliveFacturas(models.TransientModel):
    _name = 'delivery.reporte.facturas'
    _description = 'Facturas de Clientes'
    _order = 'invoice_date asc'

    treasury_id = fields.Many2one("delivery.reporte.sesenta", "Forecast")
    invoice_id = fields.Many2one("account.invoice", string="No. Factura")
    invoice_date = fields.Date("Fecha de Factura")
    date_due = fields.Date("Fecha de vencimiento")
    partner_id = fields.Many2one("res.partner", string="Cliente")
    banco = fields.Char("Banco")
    fecha_pago = fields.Date("Fecha Pago")
    state = fields.Selection([('draft', 'Borrador'), ('proforma', 'Pro-forma'),
                              ('proforma2', 'Pro-forma'), ('open', 'Abierta'),
                              ('paid', 'Pagada'), ('cancel', 'Cancelada')],
                             string="State")
    valor_orden = fields.Float("Valor de Orden",
                               digits_compute=dp.get_precision('Account'), readonly=True)
    total_fatura = fields.Float("Total Factura",
                              digits_compute=dp.get_precision('Account'), readonly=True)
    descuento = fields.Float("60 Grados",
                                digits_compute=dp.get_precision('Account'), readonly=True)
    saldo_pendiente = fields.Float("Saldo Pendiente")

    plazo_pago_id = fields.Many2one("account.payment.term", "Plazo de pago")
    numero_factura = fields.Char("Factura")
    orden_compra = fields.Char("Orde de Compra")


class AccountTreasuryForecast(models.TransientModel):
    _name = 'delivery.reporte.sesenta'
    _description = 'Reporte de Compras'
    _rec_name = 'fecha_inicio'

    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one("res.currency", "Moneda", domain=[('active', '=', True)], default=get_currency)
    name = fields.Char("Descripción")
    #Borrar
    state = fields.Selection([('draft','Borrador'),('progress','Progreso'),('done','Finalizado')], string='Estado',default='draft')
    fecha_inicio = fields.Date("Fecha de Inicio", required=True)
    fecha_final = fields.Date("Fecha Final", required=True)
    plazo_pago_id = fields.Many2one("account.payment.term", "Plazo de pago")

    invoice_ids = fields.One2many("delivery.reporte.facturas", "treasury_id", "Facturas de Clientes")

    total_descuento = fields.Float("Descuento 60 grados")
    total_valor_orden = fields.Float("Total Valor en ordenes")
    total_faturas = fields.Float("Total en Facturas")
    mes_revisar = fields.Char("Mes", track_visibility='onchange')

    @api.onchange("fecha_inicio")
    def onchangefecha(self):
        if self.fecha_inicio:
            varialble_string = datetime.strptime(self.fecha_inicio, '%Y-%m-%d')
            self.mes_revisar = varialble_string.strftime("%B")

    @api.one
    def restart(self):
        if self.invoice_ids:
            for invs in self.invoice_ids:
                invs.unlink()

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoice()
        self.get_totales()

    def get_totales(self):
        self.total_descuento = 0.0
        self.total_faturas = 0.0
        self.total_valor_orden = 0.0
        for factura in self.invoice_ids:
            self.total_descuento += factura.descuento
            self.total_faturas += factura.total_fatura
            self.total_valor_orden += factura.valor_orden

    @api.one
    def calculate_invoice(self):
        if self.plazo_pago_id:
            obj_factura = self.env["account.invoice"].search([('type', '=', 'in_invoice'), ('date_invoice', '>=', self.fecha_inicio), 
            ('date_invoice', '<=', self.fecha_final), ('state', 'in', ('open', 'paid')), ('payment_term', '=', self.plazo_pago_id.id)])  
        else:
            obj_factura = self.env["account.invoice"].search([('type', '=', 'in_invoice'), ('date_invoice', '>=', self.fecha_inicio), 
            ('date_invoice', '<=', self.fecha_final), ('state', 'in',( 'open', 'paid'))])
        obj_invoice = self.env["delivery.reporte.facturas"]
        for facturas in obj_factura:

            vals = {
                'treasury_id': self.id,
                'invoice_id': facturas.id,
                'invoice_date': facturas.date_invoice,
                'date_due': facturas.date_due,
                'numero_factura': facturas.supplier_invoice_number,
                'orden_compra': facturas.reference,
                'plazo_pago_id': facturas.payment_term.id,
                'state': facturas.state,
                'partner_id': facturas.partner_id.id,
                'valor_orden': facturas.total_compra,
                'total_fatura': facturas.total_neto_compra,
                'descuento': facturas.descuento_60,
                'saldo_pendiente': facturas.residual,
            }
            id_obj_line = obj_invoice.create(vals)
            for pago in facturas.pagos_ved_ids:
                id_obj_line.fecha_pago = pago.date_pago


    @api.multi
    def action_draft(self):
        self.write({'state' : 'draft'})

    @api.multi
    def action_progress(self):
        self.write({'state':'progress'})

    @api.multi
    def action_done(self):
        self.write({'state':'done'})

