from odoo import http
from odoo.http import request

class InternPortalOnboarding(http.Controller):

    @http.route(['/my/onboarding'], type='http', auth='user', website=True)
    def portal_onboarding(self, **kwargs):
        items = request.env['intern.onboarding'].sudo().search([('active', '=', True)], order='sequence')
        values = {'items': items}
        return request.render('praktikanten_modul.portal_onboarding', values)