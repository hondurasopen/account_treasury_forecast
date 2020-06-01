# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import date,datetime


class Facturasrango(models.Model):
    _name = 'delivery.cost.cobros.invoice'
    _description = 'Cobros/Pagos de Clientes'

    number_payment = fields.Many2one("account.voucher", string="No. Pago")
    reference = fields.Char("Referencia")
    memo = fields.Char("Referencia")
    journal_id = fields.Many2one("account.journal", "Banco")
    date = fields.Date("Fecha de Pago")
    partner_id = fields.Many2one("res.partner", string="Empresa")
    amount = fields.Float(string="Total de Factura",
                                digits_compute=dp.get_precision('Account'))
    treasury_id = fields.Many2one("account.treasury.forecast", string="Treasury")


class Deliverypagos(models.Model):
    _name = 'account.treasury.forecast.invoice'
    _description = 'Treasury Forecast Invoice'
    _order = 'invoice_date asc'

    invoice_id = fields.Many2one("account.invoice", string="No. Documento")
    numero_factura = fields.Char("# de Factura")
    invoice_date = fields.Date("Fecha de Factura")
    date_due = fields.Date(string="Fecha de Vencimiento")
    partner_id = fields.Many2one("res.partner", string="Empresa")
    state = fields.Selection([('draft', 'Borrador'), ('proforma', 'Pro-forma'),
                              ('proforma2', 'Pro-forma'), ('open', 'Abierta'),
                              ('paid', 'Pagada'), ('cancel', 'Cancelada')],
                             string="State")
    importe_abonado = fields.Float(string="Importe Pagado",
                               digits_compute=dp.get_precision('Account'))
    total_ncredito = fields.Float(string="Nota de Crédito",
                              digits_compute=dp.get_precision('Account'))
    total_amount = fields.Float(string="Total de Factura",
                                digits_compute=dp.get_precision('Account'))
    residual_amount = fields.Float(string="Saldo Pendiente",
                                   digits_compute=dp.get_precision('Account'))
    treasury_id = fields.Many2one("account.treasury.forecast", string="Treasury")


class AccountTreasuryForecast(models.Model):
    _name = 'account.treasury.forecast'
    _description = 'Treasury Forecast'

    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one("res.currency", "Moneda", required=True, domain=[('active', '=', True)], default=get_currency, help="Moneda que sera utilizada para el calculo para el flujo de efectivo")
    name = fields.Char(string="Description")
    total_bank = fields.Float(string="Total en Bancos", help="Total de los bancos de la empresa en la moneda que sera calculado el flujo de efectivo")
    #Borrar 
    total_incoming = fields.Float(string="Total de Ventas", readonly=True, help="Totales de las facturas de clientes")
    #Borrar
    state = fields.Selection([('draft','Borrador'),('progress','Progreso'),('done','Finalizado')], string='Estado',default='draft')
    start_date = fields.Date(string="Fecha de Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    check_draft = fields.Boolean(string="Borrador")
    check_proforma = fields.Boolean(string="Esperando Aprobación")
    check_done = fields.Boolean(string="Pagadas")
    check_open = fields.Boolean(string="Abiertas", default=1)
    out_invoice_ids = fields.One2many("account.treasury.forecast.invoice", "treasury_id", "Facturas de Clientes")


    cobros_ids = fields.One2many("delivery.cost.cobros.invoice","treasury_id", "Cobros/Pagos de Clientes")

    total_cobros = fields.Float(string="Total de Cobros", readonly=True)

    total_notas = fields.Float(string="Notas de Crédito", readonly=True)
    saldo_pendiente = fields.Float(string="Total de cobros pendientes", readonly=True)

    @api.one
    @api.constrains('end_date', 'start_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise exceptions.Warning(
                _('Error!:: End date is lower than start date.'))

    @api.one
    @api.constrains('check_draft', 'check_proforma', 'check_open')
    def check_filter(self):
        if not self.check_draft and not self.check_proforma and not self.check_open and not self.check_done:
            raise exceptions.Warning(_('Error!:: There is no any filter checked.'))

    @api.one
    def restart(self):
        self.out_invoice_ids.unlink()
        self.cobros_ids.unlink()
        return True

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoices()
        self.get_cobros()
        self.calculate_total()
        return True

    @api.one
    def calculate_total(self):
        if self.out_invoice_ids:
            saldo = 0.0
            notas = 0.0
            amount = 0.0
            for line in self.out_invoice_ids:
                saldo += line.residual_amount
                notas += line.total_ncredito
                amount += line.total_amount
            self.total_incoming = amount
            self.total_notas = notas
            self.saldo_pendiente = saldo

    @api.one
    def get_cobros(self):
        obj_cobro = self.env["account.voucher"]
        cobros_treasury_obj = self.env["delivery.cost.cobros.invoice"]
        cobro_ids = obj_cobro.search([('date', '>=', self.start_date), ('date', '<=', self.end_date), ('state', '=', 'posted')])
        cobros = 0.0
        for payment in cobro_ids:
            values = {
                'number_payment': payment.id,
                'date': payment.date,
                'journal_id': payment.journal_id.id,
                'partner_id': payment.partner_id.id,
                'amount': payment.amount,
                'treasury_id': self.id,
                'reference': payment.reference,
                'memo': payment.name,
                    }
            new_id = cobros_treasury_obj.create(values)
            if new_id:
                cobros += payment.amount
        #self.total_cobros = cobros


    @api.one
    def calculate_invoices(self):
        invoice_obj = self.env['account.invoice']
        treasury_invoice_obj = self.env['account.treasury.forecast.invoice']
        new_invoice_ids = []
        in_invoice_lst = []
        out_invoice_lst = []
        state = []
        self.total_incoming = 0
        self.total_invoice_out = 0
        if self.check_draft:
            state.append("draft")
        if self.check_open:
            state.append("open")
        if self.check_done:
            state.append("paid")
        invoice_ids = invoice_obj.search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date),('type', '=', 'out_invoice'),  ('state', 'in', tuple(state))])

        for invoice_o in invoice_ids:
            values = {
                'invoice_id': invoice_o.id,
                'date_due': invoice_o.date_due,
                'invoice_date': invoice_o.date_invoice,
                'partner_id': invoice_o.partner_id.id,
                'treasury_id': self.id,
                'numero_factura': invoice_o.internal_number,
                #'journal_id': invoice_o.journal_id.id,
                #'currency_id': invoice_o.currency_id.id,
                'state': invoice_o.state,
                #'base_amount': invoice_o.amount_untaxed,
                #'tax_amount': invoice_o.amount_tax,
                'total_amount': invoice_o.amount_total,
                'residual_amount': invoice_o.residual,
                'importe_abonado': invoice_o.importe_abonado,
                'total_ncredito': invoice_o.total_ncredito, 
            }
            new_id = treasury_invoice_obj.create(values)
        return 


    @api.multi
    def action_draft(self):
        self.write({'state' : 'draft'})

    @api.multi
    def action_progress(self):
        self.write({'state':'progress'})

    @api.multi
    def action_done(self):
        self.write({'state':'done'})

