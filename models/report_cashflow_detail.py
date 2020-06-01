from openerp import api, models
import time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class reporte(models.AbstractModel):
    _name = 'report.accout_treasury_forecast.report_cashflow_detail'

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('account_treasury_forecast.report_cashflow_detail')
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            }
        return report_obj.render("account_treasury_forecast.report_cashflow_detail",docargs)


