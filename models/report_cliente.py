# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import date,datetime


class DeliveFacturasCliente(models.Model):
    _name = 'account.delivery.forecast.product.cliente'
    _description = 'Productos'
    _order = 'total_venta desc, porcentaje_sale desc'

    product_id = fields.Many2one("product.product", "Producto")
    galonaje = fields.Float("Total Galonaje")
    total_venta = fields.Float("Total de Ventas")
    treasury_id = fields.Many2one("account.delivery.forecast.cliente", "Forecast")
    porcentaje_sale = fields.Float("Ventas %")
    porcentaje_unidades = fields.Float("Producto %")


class DeliveFacturasCliente(models.Model):
    _name = 'account.delivery.forecast.invoice.cliente'
    _description = 'Facturas de Clientes'
    _order = 'invoice_date asc'

    treasury_id = fields.Many2one("account.delivery.forecast.cliente","Forecast")
    invoice_id = fields.Many2one("account.invoice", string="No. Factura")
    invoice_date = fields.Date("Fecha de Factura")
    date_due = fields.Date(string="Fecha de Vencimiento")
    partner_id = fields.Many2one("res.partner", string="Cliente")
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
    costo_flete = fields.Float(string="Costo de Flete",
                                   digits_compute=dp.get_precision('Account'))
    utilidad = fields.Float(string="Utilidad por factura",
                                   digits_compute=dp.get_precision('Account'))

    pedido_venta_id = fields.Many2one("sale.order", "Pedido de ventas")
    total_galones = fields.Float("Total de Galones")
    costo_combustible = fields.Float("Totol Costo")


class AccountTreasuryForecastCliente(models.Model):
    _name = 'account.delivery.forecast.cliente'
    _description = 'Cadena de Suministro'

    def get_currency(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one("res.currency", "Moneda", domain=[('active', '=', True)], default=get_currency)
    name = fields.Char(string="Description")
    cliente_id = fields.Many2one("res.partner", "Cliente", required=True, domain=[('customer', '=', True)])
    total_incoming = fields.Float(string="Total de Ventas", readonly=True, help="Totales de las facturas de clientes")
    #Borrar
    state = fields.Selection([('draft','Borrador'),('progress','Progreso'),('done','Finalizado')], string='Estado',default='draft')
    start_date = fields.Date(string="Fecha de Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    check_draft = fields.Boolean(string="Borrador")
    check_proforma = fields.Boolean(string="Esperando Aprobación")
    check_done = fields.Boolean(string="Pagadas", default=1)
    check_open = fields.Boolean(string="Abiertas", default=1)
    out_invoice_ids = fields.One2many("account.delivery.forecast.invoice.cliente", "treasury_id", "Facturas de Clientes")

    product_forecast_ids = fields.One2many("account.delivery.forecast.product.cliente", "treasury_id", "Venta de Productos")

    total_notas = fields.Float(string="Notas de Crédito", readonly=True)
    total_fletes = fields.Float("Total de Fletes", readonly=True)
    total_combustible = fields.Float("Total Combustible", readonly=True)
    total_galonaje = fields.Float("Total de Galonaje", readonly=True)
    utilidad_bruta = fields.Float("Utilidad Bruta", readonly=True)
    costos_directos = fields.Float("Total costos", readonly=True)
    costo_porcentual = fields.Float("Costo combustible %", readonly=True)
    costo_transporte = fields.Float("Costo de tranporte %", readonly=True)
    count_facturas =  fields.Integer("Número de Ventas", readonly=True)
    total_gal = fields.Float("Galones facturados")

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
        self.total_combustible = 0.0
        self.total_fletes = 0.0
        self.total_notas = 0.0
        self.count_facturas = 0
        if self.out_invoice_ids:
            for invs in self.out_invoice_ids:
                invs.unlink()
        if self.product_forecast_ids:
            for prods in self.product_forecast_ids:
                prods.unlink()
        return True

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoices()
        self.get_product()
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
        if self.out_invoice_ids:
            saldo = 0.0
            notas = 0.0
            amount = 0.0
            fletes = 0.0
            costo = 0.0
            galonaje = 0.0
            contador = 0.0
            for line in self.out_invoice_ids:
                saldo += line.residual_amount
                notas += line.total_ncredito
                amount += line.total_amount
                fletes += line.costo_flete
                costo += line.costo_combustible
                galonaje += line.total_galones
                contador += 1
            self.count_facturas = contador
            self.total_incoming = amount
            self.total_notas = notas
            self.total_fletes = fletes
            self.total_combustible = costo
            self.total_galonaje = galonaje
            self.costos_directos = self.total_combustible + self.total_fletes
            if not self.total_incoming == self.total_notas:
                self.costo_porcentual = (self.total_combustible / (self.total_incoming - self.total_notas)) * 100
                self.costo_transporte = (self.total_fletes / (self.total_incoming - self.total_notas)) * 100
            self.utilidad_bruta = self.total_incoming - self.total_combustible -self.total_fletes- self.total_notas

        if self.product_forecast_ids and  self.total_incoming > 0:
            gals = 0.0
            for line in self.product_forecast_ids:
                gals += line.galonaje
                line.write({'porcentaje_sale': ((line.total_venta / self.total_incoming) * 100)})
                line.write({'porcentaje_unidades': ((line.galonaje / self.total_incoming) * 100)})
            self.total_gal = gals

    @api.one
    def calculate_invoices(self):
        invoice_obj = self.env['account.invoice']
        treasury_invoice_obj = self.env['account.delivery.forecast.invoice.cliente']
        state = []
        self.total_incoming = 0
        self.total_invoice_out = 0
        if self.check_draft:
            state.append("draft")
        if self.check_open:
            state.append("open")
        if self.check_done:
            state.append("paid")
        invoice_ids = invoice_obj.search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), 
            ('type', '=','out_invoice'), ('partner_id', '=', self.cliente_id.id), ('state', 'in', tuple(state))])
        pedido_ventas_id = False
        for invoice_o in invoice_ids:
            values = {
                'treasury_id': self.id,
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
                'importe_abonado': invoice_o.importe_abonado,
                'total_ncredito': invoice_o.total_ncredito,
            }
            pedido_ventas_id = self.env["sale.order"].search([('name', '=', invoice_o.origin), ('state', 'not in', ['draft', 'cancel'])])
            if pedido_ventas_id:
                values["costo_flete"] = pedido_ventas_id.total_flete
                values["pedido_venta_id"] = pedido_ventas_id.id
                if pedido_ventas_id.order_line:
                    galonaje = 0.0
                    costo = 0.0
                    for line in pedido_ventas_id.order_line:
                        galonaje += line.product_uom_qty
                        costo += (line.purchase_price * line.product_uom_qty)
                    values["total_galones"] =  galonaje
                    values["costo_combustible"] = costo

            new_id = treasury_invoice_obj.create(values)
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

