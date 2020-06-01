# -*- encoding: utf-8 -*-
from openerp import fields, models, exceptions, api, _
import base64
import csv
import cStringIO
from openerp.exceptions import except_orm, Warning, RedirectWarning

class NotaCreditoWizard(models.Model):
    _name = "vedd.grados.factura.proveedor"
    _rec_name = "supplier_id"


    start_date = fields.Date("Fecha de inicio")
    end_date = fields.Date("Fecha final")
    supplier_id = fields.Many2one("res.partner", "Proveedor")
    line_ids = fields.One2many("vedd.grados.factura.proveedor.line", "parent_id", "Detalle")
    monto_nota = fields.Float("Total Notas débito")
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Liquidado')], default='draft' , string="Estado")
    journal_id = fields.Many2one("account.journal", "Diario")
    move_id = fields.Many2one("account.move", "Asiento")

    @api.multi
    def unlink(self):
        if (self.state == 'done'):
            raise exceptions.Warning(_('Error:: No se puede borrar registros validados.'))
        return super(NotaCreditoWizard, self).unlink()


    @api.multi
    def generate_journal_entries(self):
        if self.line_ids:
            period_id = self.env["account.period"].with_context(self._context).find(self.end_date)[:1]
            self.journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            obj_move = self.env["account.move"]
            lineas = []
            vals_debit = {
                'debit': 0.0,
                'credit': self.monto_nota,
                'amount_currency': 0.0,
                'name': 'Liquidación 60 grados',
                'account_id': self.journal_id.default_credit_account_id.id,
                'partner_id': self.supplier_id.id,
                'date': self.end_date,
            }
            vals_credit = {
                'debit': self.monto_nota,
                'credit': 0.0,
                'amount_currency': 0.0,
                'name': 'Liquidación 60 grados',
                'account_id': self.supplier_id.property_account_payable.id,
                'partner_id': self.supplier_id.id,
                'date': self.end_date,
            }
            lineas.append((0, 0, vals_debit))
            lineas.append((0, 0, vals_credit))
            vals = {
                'journal_id': self.journal_id.id,
                'date': self.end_date,
                'ref': 'Liquidación de 60 grados',
                'period_id': period_id.id,
                'line_id': lineas,
            }
            id_move = obj_move.create(vals)
            if id_move :
                self.write({'state': 'done'})
                self.move_id = id_move.id
        else:
            raise exceptions.Warning(_('Error:: No existen registros.'))

    @api.one
    def get_invoice_supplier(self):
        if self.line_ids:
            self.line_ids.unlink()
            self.monto_nota = 0
        state_invoice = []
        state_invoice.append('open')
        state_invoice.append('paid')
        inv_obj = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), 
            ('type', '=', 'in_invoice'), ('state', 'in', tuple(state_invoice)), ('partner_id', '=', self.supplier_id.id)])
        for invoice in inv_obj:
            line = self.env["vedd.grados.factura.proveedor.line"]
            if invoice.nota_debito_id or not invoice.factura_credito:
                vals = {
                    'parent_id': self.id,
                    'invoice_id': invoice.id,
                    'total': invoice.amount_total,
                    'total_orden': invoice.total_compra,
                    'descuento_60': invoice.descuento_60,
                    'numero_orden': invoice.reference,
                    'factura': invoice.supplier_invoice_number,
                    'fecha': invoice.date_invoice,
                    'saldo_pendiente': invoice.residual,
                    'nota_debito_id': invoice.nota_debito_id.id,
                    'move_note_id': invoice.nota_debito_id.move_id.id,
                }
                if invoice.nota_debito_id:
                    vals["has_debit_note"] = True
                else:
                    vals["has_debit_note"] = False
                inv_line_id = line.create(vals)
                if inv_line_id:
                    self.monto_nota += invoice.descuento_60


class NotaCreditoWizardLine(models.Model):
    _name = "vedd.grados.factura.proveedor.line"

    parent_id = fields.Many2one("vedd.grados.factura.proveedor", "Parent")
    invoice_id = fields.Many2one("account.invoice", "Factura")
    total = fields.Float("Total")
    total_orden = fields.Float("Total orden")
    descuento_60 = fields.Float("Descuento 60")
    numero_orden = fields.Char("# Orden")
    factura = fields.Char("# Factura")
    fecha = fields.Date("Fecha")
    saldo_pendiente = fields.Float("Saldo Pendiente")
    nota_debito_id = fields.Many2one("nota.debito.factura.proveedores", "Nota debito")
    has_debit_note = fields.Boolean("Nota de débito")
    move_note_id = fields.Many2one("account.move", "Asiento ND")
