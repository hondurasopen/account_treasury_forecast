# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import datetime, timedelta


class VeddepessaClienteLine(models.TransientModel):
    _name = 'veddepessa.sale.gals.qty.line'

    partner_id = fields.Many2one("res.partner", "Cliente")
    gal_diesel = fields.Float("Galones Diesel")
    gal_super = fields.Float("Galones Super")
    gal_regular = fields.Float("Galones Regular")
    gal_kerosene = fields.Float("Galones Kerosene")
    parent_id = fields.Many2one("veddepessa.sale.gals.qty", "Forecast")



class AccountTreasuryForecastCliente(models.TransientModel):
    _name = 'veddepessa.sale.gals.qty'


    name = fields.Char(string="Description")
    #Borrar
    state = fields.Selection([('draft','Borrador'),('progress','Progreso'),('done','Finalizado')], string='Estado',default='draft')
    start_date = fields.Date(string="Fecha de Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    name = fields.Char("Mes")
    tipo_cliente = fields.Selection([('Distribuidoras', 'Distribuidoras'), ('Gasolinera', 'Gasolineras')], string='Tipo de Cliente')
    total_galonaje = fields.Float("Total de Galonaje", readonly=True)
    line_ids = fields.One2many("veddepessa.sale.gals.qty.line", "parent_id", "Clientes")

    @api.onchange("start_date")
    def onchangefecha(self):
        if self.start_date:
            varialble_string = datetime.strptime(self.start_date, '%Y-%m-%d')
            self.name = varialble_string.strftime("%B")


    @api.one
    @api.constrains('end_date', 'start_date')
    def check_date(self):
        if self.start_date > self.end_date:
            raise exceptions.Warning(
                _('Error!:: La fecha final debe de ser mayorn que la fecha inicial.'))

    @api.one
    def restart(self):
        if self.line_ids:
            for prods in self.line_ids:
                prods.unlink()
        return True

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoices()
        #self.get_product()
        self.calculate_total()

    @api.one
    def get_product(self):
        obj_product = self.env["product.product"].search([('sale_ok', '=', True)])
        obj_forecast_product = self.env["account.delivery.forecast.product.cliente"]
        treasury_invoice_obj = self.env['account.delivery.forecast.invoice.cliente'].search([('treasury_id', '=', self.id)])
        for product in obj_product:
            value = {
            'product_id': product.id,
            'treasury_id': self.id,
                }
            id_forecast_prod = obj_forecast_product.create(value)
            if id_forecast_prod:
                sum_line = 0.0
                qty = 0.0
                for forecast in treasury_invoice_obj:
                    for line in forecast.invoice_id.invoice_line:
                        if line.product_id.id == product.id:
                            sum_line += line.price_subtotal
                            qty += line.quantity
                id_forecast_prod.write({'total_venta': sum_line, 'galonaje': qty})


    def calculate_total(self):
        if self.line_ids:
            galonaje = 0.0
            for line in self.line_ids:
                galonaje += line.gal_diesel
            self.total_galonaje = galonaje


    @api.one
    def calculate_invoices(self):
        invoice_obj = self.env['account.invoice']
        treasury_invoice_obj = self.env['veddepessa.sale.gals.qty.line']
        state = []
        state.append("open")
        state.append("paid")
        invoice_ids = invoice_obj.search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=','out_invoice'), 
            ('state', 'in', tuple(state)), ('partner_id.tipo_cliente', '=', self.tipo_cliente), ('nota_debito', '=', False) ])

        for invoice_o in invoice_ids:
            obj_qty = self.env["veddepessa.sale.gals.qty.line"]
            obj_line_ids = self.env["veddepessa.sale.gals.qty.line"].search([('parent_id', '=', self.id), 
                ('partner_id', '=', invoice_o.partner_id.id)])
            gals_diesel = 0
            gals_super = 0
            gals_regular = 0
            gals_kerosene = 0
            if obj_line_ids:
                for line_invoice in  invoice_o.invoice_line:
                    if line_invoice.product_id.tipo_gas == 'diesel':
                        gals_diesel = line_invoice.quantity
                        obj_line_ids.gal_diesel += gals_diesel
                    if line_invoice.product_id.tipo_gas == 'super':
                        gals_super = line_invoice.quantity
                        obj_line_ids.gal_super += gals_super
                    if line_invoice.product_id.tipo_gas == 'regular':
                        gals_regular = line_invoice.quantity
                        obj_line_ids.gal_regular += gals_regular
                    if line_invoice.product_id.tipo_gas == 'kerosene':
                        gals_kerosene = line_invoice.quantity
                        obj_line_ids.gal_kerosene += gals_kerosene
            else:
                values = {
                    'partner_id': invoice_o.partner_id.id,
                    'parent_id': self.id,
                }
                for line_invoice in  invoice_o.invoice_line:
                    if line_invoice.product_id.tipo_gas == 'diesel':
                        gals_diesel = line_invoice.quantity
                        values["gal_diesel"] = gals_diesel
                    if line_invoice.product_id.tipo_gas == 'super':
                        gals_super = line_invoice.quantity
                        values["gal_super"] = gals_super
                    if line_invoice.product_id.tipo_gas == 'regular':
                        gals_regular = line_invoice.quantity
                        values["gal_regular"] = gals_regular
                    if line_invoice.product_id.tipo_gas == 'kerosene':
                        gals_kerosene = line_invoice.quantity
                        values["gal_kerosene"] = gals_kerosene

                new_id = obj_qty.create(values)
        return True



    @api.multi
    def action_draft(self):
        self.write({'state' : 'draft'})

    @api.multi
    def action_progress(self):
        self.write({'state':'progress'})

    @api.multi
    def action_done(self):
        self.write({'state':'done'})

