# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import date,datetime


class FacturaCliente(models.TransientModel):
    _name = 'account.antiguedad.saldos.clientes'
    _order = 'invoice_date asc'
    _rec_name = 'invoice_date'

    invoice_id = fields.Many2one("account.invoice", string="No. Documento")
    numero_factura = fields.Char("# de Factura")
    invoice_date = fields.Date("Fecha de Factura")
    date_due = fields.Date(string="Fecha de Vencimiento")
    partner_id = fields.Many2one("res.partner", string="Empresa")

    importe_abonado = fields.Float(string="Importe Pagado", digits_compute=dp.get_precision('Account'))
    total_ncredito = fields.Float(string="Nota de Crédito", digits_compute=dp.get_precision('Account'))
    total_amount = fields.Float(string="Total de Factura", digits_compute=dp.get_precision('Account'))
    residual_amount = fields.Float(string="Saldo Pendiente", digits_compute=dp.get_precision('Account'))
    obj_parent = fields.Many2one("account.antiguedad", string="Antiguedad de Saldos")
    old_pay = fields.Boolean("Indicador", default=False)


class AntiguedadSaldos(models.TransientModel):
    _name = 'account.antiguedad'

    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one("res.currency", "Moneda", required=True, domain=[('active', '=', True)], default=get_currency, help="Moneda que sera utilizada para el calculo para el flujo de efectivo")
    name = fields.Char(string="Description")
    total_facturado = fields.Float(string="Total de Ventas", readonly=True, help="Totales de las facturas de clientes")
    #Borrar
    start_date = fields.Date(string="Fecha de Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    
    out_invoice_ids = fields.One2many("account.antiguedad.saldos.clientes", "obj_parent", "Facturas de Clientes")

    total_notas = fields.Float(string="Notas de Crédito", readonly=True)
    saldo_pendiente = fields.Float(string="Total de cobros pendientes", readonly=True)
    total_pagos = fields.Float(string="Total de pagos", readonly=True)

    @api.one
    @api.constrains('end_date', 'start_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise exceptions.Warning(_('Error!:: End date is lower than start date.'))

    @api.one
    def restart(self):
        self.out_invoice_ids.unlink()
        return True

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoices()
        self.calculate_total()
        return True

    @api.one
    def calculate_total(self):
        if self.out_invoice_ids:
            pagos = 0
            notas = 0.0
            amount = 0.0
            for line in self.out_invoice_ids:
                notas += line.total_ncredito
                amount += line.total_amount
                pagos += line.importe_abonado
            self.total_facturado = amount
            self.total_notas = notas
            self.total_pagos = pagos
            self.saldo_pendiente = self.total_facturado - self.total_pagos - self.total_notas


    @api.one
    def calculate_invoices(self):
        invoice_obj = self.env['account.invoice']
        treasury_invoice_obj = self.env['account.antiguedad.saldos.clientes']
        state = []
        self.total_facturado = 0
        state.append("open")
        state.append("paid")
        invoice_ids = invoice_obj.search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date),('type', '=', 'out_invoice'),  ('state', 'in', tuple(state))])

        for invoice_o in invoice_ids:
            values = {
                'invoice_id': invoice_o.id,
                'date_due': invoice_o.date_due,
                'invoice_date': invoice_o.date_invoice,
                'partner_id': invoice_o.partner_id.id,
                'obj_parent': self.id,
                'numero_factura': invoice_o.internal_number,
                'total_amount': invoice_o.amount_total,
                'residual_amount': 0.0,
                'importe_abonado': 0.0,
                'total_ncredito': invoice_o.total_ncredito, 
            }
            new_id = treasury_invoice_obj.create(values)
            if new_id:
                new_id.total_ncredito += invoice_o.total_ncredito
                for line_pay in invoice_o.move_lines:
                    if line_pay.move_id.date >= self.start_date and line_pay.move_id.date <= self.end_date:
                        new_id.importe_abonado = new_id.importe_abonado + line_pay.credit
                    if line_pay.move_id.date < invoice_o.date_invoice:
                        new_id.old_pay = True
                for pago_ved_lin in invoice_o.pagos_ved_customer_ids:
                    if pago_ved_lin.pago_id.state == 'paid' and pago_ved_lin.pago_id.date >= self.start_date and pago_ved_lin.pago_id.date <= self.end_date:
                        new_id.importe_abonado = new_id.importe_abonado + pago_ved_lin.monto_pago
                    if pago_ved_lin.pago_id.date < invoice_o.date_invoice:
                        new_id.old_pay = True
        return
