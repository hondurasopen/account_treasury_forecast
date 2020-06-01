# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import date,datetime



class AccountTreasuryForecastCliente(models.TransientModel):
    _name = 'libro.ventas.ved'
    _description = 'Libro de ventas'


    name = fields.Char(string="Description", default="Libro de ventas")
    start_date = fields.Date(string="Fecha de Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)

    out_invoice_ids = fields.One2many("libro.ventas.ved.line", "obj_parent", "Facturas de Clientes")

    total_notas = fields.Float("Notas de Crédito", readonly=True)
    total_factura = fields.Float("Total de Ventas", readonly=True, help="Totales de las facturas de clientes")
    total_isv = fields.Float("Total ISV", readonly=True)
    total_neto = fields.Float("Total Neto", readonly=True)

    @api.one
    @api.constrains('end_date', 'start_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise exceptions.Warning(
                _('Error!:: La fecha final debe ser mayor que la fecha inicial.'))

    @api.one
    def restart(self):
        self.total_notas = 0.0
        self.total_factura = 0.0
        self.total_isv = 0.0
        self.total_neto = 0
        if self.out_invoice_ids:
            for invs in self.out_invoice_ids:
                invs.unlink()

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoices()
        self.calculate_total()

    @api.multi
    def calculate_total(self):
        if self.out_invoice_ids:
            for l in self.out_invoice_ids:
                self.total_factura += l.total_amount
                self.total_notas += l.total_ncredito
            self.total_neto = self.total_factura - self.total_notas


    @api.one
    def calculate_invoices(self):
        invoice_obj = self.env['account.invoice']
        treasury_invoice_obj = self.env['libro.ventas.ved.line']
        state = []

        state.append("open")
        state.append("paid")

        invoice_ids = invoice_obj.search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), 
            ('type', '=', 'out_invoice'), ('state', 'in', tuple(state))])

        for invoice_o in invoice_ids:
            values = {
                'obj_parent': self.id,
                'invoice_id': invoice_o.id,
                'date_due': invoice_o.date_due,
                'invoice_date': invoice_o.date_invoice,
                'partner_id': invoice_o.partner_id.id,
                #'journal_id': invoice_o.journal_id.id,
                #'currency_id': invoice_o.currency_id.id,
                'state': invoice_o.state,
                #'base_amount': invoice_o.amount_untaxed,
                #'tax_amount': invoice_o.amount_tax,
                'total_amount': invoice_o.amount_total,
                'residual_amount': invoice_o.residual,
            }
            obj_nota_credito = self.env["tipo.nota.debito.factura"].search([('name', '=', 'Descuento 60 grados')])
            obj_credito = self.env["account.invoice"].search([('origin', '=', invoice_o.internal_number), 
                ('tipo_nota_credito', '=', obj_nota_credito.id)], limit=1)
            print "*" * 200
            print obj_credito
            print "*" * 200

            if obj_credito:
                values["nota_credito"] = obj_credito.id
                values["total_ncredito"] = obj_credito.amount_total

            new_id = treasury_invoice_obj.create(values)
        return True



class AccountInvoiceLine(models.TransientModel):
    _name = 'libro.ventas.ved.line'
    _description = 'Facturas de Clientes'
    _order = 'invoice_date asc'

    obj_parent = fields.Many2one("libro.ventas.ved", "Forecast")
    invoice_id = fields.Many2one("account.invoice", string="No. Factura")
    internal_number = fields.Char("# Factura", related="invoice_id.internal_number")
    nota_credito = fields.Many2one("account.invoice", "Nota de debito")
    num_nota = fields.Char("# Nota Cŕedito", related="nota_credito.internal_number")

    invoice_date = fields.Date("Fecha de Factura")
    date_due = fields.Date(string="Fecha de Vencimiento")
    partner_id = fields.Many2one("res.partner", string="Cliente")

    state = fields.Selection([('draft', 'Borrador'), ('proforma', 'Pro-forma'),
                              ('proforma2', 'Pro-forma'), ('open', 'Abierta'),
                              ('paid', 'Pagada'), ('cancel', 'Cancelada')],
                             string="State")
    total_ncredito = fields.Float(string="Nota de Crédito",
                              digits_compute=dp.get_precision('Account'))
    total_amount = fields.Float(string="Total de Factura",
                                digits_compute=dp.get_precision('Account'))
    residual_amount = fields.Float(string="Saldo Pendiente",
                                   digits_compute=dp.get_precision('Account'))