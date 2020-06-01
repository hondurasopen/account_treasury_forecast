# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import date,datetime


class DeliveFacturas(models.Model):
    _name = 'delivery.reporte.compras'
    _description = 'Facturas de Clientes'
    _order = 'invoice_date asc'

    treasury_id = fields.Many2one("delivery.reporte.compras", "Forecast")
    compra_id = fields.Many2one("purchase.order", "Compra")
    invoice_id = fields.Many2one("account.invoice", string="No. Factura")
    invoice_date = fields.Date("Fecha de Factura")
    date_due = fields.Date(string="Fecha de Vencimiento")
    partner_id = fields.Many2one("res.partner", string="Cliente")
    state = fields.Char("Status")
    valor_orden = fields.Float("Valor de Orden",
                               digits_compute=dp.get_precision('Account'), readonly=True)
    total_fatura = fields.Float("Total Factura",
                              digits_compute=dp.get_precision('Account'), readonly=True)
    descuento = fields.Float("60 Grados",
                                digits_compute=dp.get_precision('Account'), readonly=True)

    plazo_pago_id = fields.Many2one("account.payment.term", "Plazo de pago")
    numero_factura = fields.Char("Factura")
    orden_compra = fields.Char("Orde de Compra")

class AccountTreasuryForecast(models.Model):
    _name = 'delivery.reporte.compras'
    _description = 'Reporte 60 grados'
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

    invoice_ids = fields.One2many("delivery.reporte.compras", "treasury_id", "Facturas de Clientes")

    total_descuento = fields.Float("Descuento 60 grados")
    total_valor_orden = fields.Float("Total Valor en ordenes")
    total_faturas = fields.Float("Total en Facturas")


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
            obj_factura = self.env["purchase.order"].search([ ('date_order', '>=', self.fecha_inicio), 
            ('date_order', '<=', self.fecha_final), ('state', 'in', 'approved'), ('payment_term_id', '=', self.plazo_pago_id.id)])  
        else:
            obj_factura = self.env["purchase.order"].search([('date_order', '>=', self.fecha_inicio), 
            ('date_order', '<=', self.fecha_final), ('state', 'in', 'approved')])
        obj_invoice = self.env["delivery.reporte.compras"]
        for facturas in obj_factura:

            vals = {
                'treasury_id': self.id,
                'compra_id': facturas.id,
                'invoice_date': facturas.date_order,
                'numero_factura': facturas.supplier_invoice_number,
                'orden_compra': facturas.partner_ref,
                'plazo_pago_id': facturas.payment_term_id.id,
                'state': facturas.state,
                'partner_id': facturas.partner_id.id,
                'valor_orden': facturas.amount_total,
            }

            id_obj_line = obj_invoice.create(vals)



    @api.multi
    def action_draft(self):
        self.write({'state' : 'draft'})

    @api.multi
    def action_progress(self):
        self.write({'state':'progress'})

    @api.multi
    def action_done(self):
        self.write({'state':'done'})

