# -*- encoding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, exceptions, _
from datetime import datetime, timedelta


class GallonsCityLine(models.TransientModel):
    _name = 'veddepessa.sale.city.line'

    city_id = fields.Many2one("delivery.cities", "Ciudad")
    gal_diesel = fields.Float("Galones Diesel")
    gal_super = fields.Float("Galones Super")
    gal_regular = fields.Float("Galones Regular")
    gal_kerosene = fields.Float("Galones Kerosene")
    parent_id = fields.Many2one("veddepessa.sale.city", "Reporte")


class GallonsDeoartmentLine(models.TransientModel):
    _name = 'veddepessa.sale.department.line'

    state_id = fields.Many2one("res.country.state", "Ciudad")
    gal_diesel = fields.Float("Galones Diesel")
    gal_super = fields.Float("Galones Super")
    gal_regular = fields.Float("Galones Regular")
    gal_kerosene = fields.Float("Galones Kerosene")
    parent_id = fields.Many2one("veddepessa.sale.city", "Reporte")


class GallonCity(models.TransientModel):
    _name = 'veddepessa.sale.city'


    name = fields.Char(string="Description")
    #Borrar
    start_date = fields.Date(string="Fecha de Inicio", required=True)
    end_date = fields.Date(string="Fecha Final", required=True)
    name = fields.Char("Mes")
    total_galonaje = fields.Float("Total de Galonaje", readonly=True)
    line_ids = fields.One2many("veddepessa.sale.city.line", "parent_id", "Ciudades")
    department_ids = fields.One2many("veddepessa.sale.department.line", "parent_id", "Departamentos")


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
            for l in self.line_ids:
                l.unlink()
        if self.department_ids:
            for l in self.department_ids:
                l.unlink()
        return True

    @api.multi
    def button_calculate(self):
        self.restart()
        self.calculate_invoices()
        self.set_state()
        self.calculate_total()


    def calculate_total(self):
        if self.line_ids:
            galonaje = 0.0
            for line in self.line_ids:
                galonaje += line.gal_diesel
            self.total_galonaje = galonaje

    @api.multi
    def set_state(self):
        if self.line_ids:
            for department in self.line_ids:
                obj_depto_ids = self.env["veddepessa.sale.department.line"].search([('parent_id', '=', self.id), 
                    ('state_id', '=', department.city_id.departamento_id.id)])
                gals_diesel = 0
                gals_super = 0
                gals_regular = 0
                gals_kerosene = 0
                if obj_depto_ids:
                    if department.gal_diesel > 0:
                        obj_depto_ids.gal_diesel += department.gal_diesel
                    if department.gal_super > 0:
                        obj_depto_ids.gal_super += department.gal_super
                    if department.gal_regular > 0:
                        obj_depto_ids.gal_regular += department.gal_regular
                    if department.gal_kerosene > 0:
                        obj_depto_ids.gal_kerosene += department.gal_kerosene
                else:
                    obj_qty = self.env["veddepessa.sale.department.line"]
                    values = {
                    'state_id': department.city_id.departamento_id.id,
                    'parent_id': self.id,
                    }
                    if department.gal_diesel > 0:
                        gals_diesel = department.gal_diesel
                        values["gal_diesel"] = gals_diesel
                    if department.gal_super > 0:
                        gals_super = department.gal_super
                        values["gal_super"] = gals_super
                    if department.gal_regular > 0:
                        gals_regular = department.gal_regular
                        values["gal_regular"] = gals_regular
                    if department.gal_kerosene > 0:
                        gals_kerosene = department.gal_kerosene
                        values["gal_kerosene"] = gals_kerosene

                    new_id = obj_qty.create(values)

    @api.one
    def calculate_invoices(self):
        state_sale = []
        state_sale.append('manual')
        state_sale.append('progress')
        state_sale.append('shipping_except')
        state_sale.append('invoice_except')
        state_sale.append('done')
        
        sale_ids = self.env["sale.order"].search([('date_order', '>=', self.start_date), ('date_order', '<=', self.end_date), ('state', 'in', tuple(state_sale))])
        for sale in sale_ids:
            for sale_line in sale.order_line:
                obj_line_ids = self.env["veddepessa.sale.city.line"].search([('parent_id', '=', self.id), 
                    ('city_id', '=', sale_line.ruta.name.id)])
                gals_diesel = 0
                gals_super = 0
                gals_regular = 0
                gals_kerosene = 0
                if obj_line_ids:
                    if sale_line.product_id.tipo_gas == 'diesel':
                        gals_diesel = sale_line.product_uom_qty
                        obj_line_ids.gal_diesel += gals_diesel
                    if sale_line.product_id.tipo_gas == 'super':
                        gals_super = sale_line.product_uom_qty
                        obj_line_ids.gal_super += gals_super
                    if sale_line.product_id.tipo_gas == 'regular':
                        gals_regular = sale_line.product_uom_qty
                        obj_line_ids.gal_regular += gals_regular
                    if sale_line.product_id.tipo_gas == 'kerosene':
                        gals_kerosene = sale_line.product_uom_qty
                        obj_line_ids.gal_kerosene += gals_kerosene
                else:
                    obj_qty = self.env["veddepessa.sale.city.line"]
                    values = {
                    'city_id': sale_line.ruta.name.id,
                    'parent_id': self.id,
                    }
                    if sale_line.product_id.tipo_gas == 'diesel':
                        gals_diesel = sale_line.product_uom_qty
                        values["gal_diesel"] = gals_diesel
                    if sale_line.product_id.tipo_gas == 'super':
                        gals_super = sale_line.product_uom_qty
                        values["gal_super"] = gals_super
                    if sale_line.product_id.tipo_gas == 'regular':
                        gals_regular = sale_line.product_uom_qty
                        values["gal_regular"] = gals_regular
                    if sale_line.product_id.tipo_gas == 'kerosene':
                        gals_kerosene = sale_line.product_uom_qty
                        values["gal_kerosene"] = gals_kerosene

                    new_id = obj_qty.create(values)
