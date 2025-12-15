import base64

from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class InternPortalContracts(http.Controller):

    @http.route(['/my/intern-contracts', '/my/intern-contracts/<int:contract_id>'], type='http', auth='public', website=True)
    def portal_intern_contracts(self, contract_id=None, **kwargs):
        partner = request.env.user.partner_id
        Contract = request.env['intern.contract']
        domain = [('intern_id.partner_id', '=', partner.id)]
        contracts = Contract.search(domain, order='create_date desc')

        selected = None
        if contract_id:
            selected = Contract.search([('id', '=', contract_id)] + domain, limit=1)

        values = {
            'contracts': contracts,
            'selected': selected,
        }
        return request.render('praktikanten_modul_vertraege.portal_intern_contracts', values)

    @http.route(['/my/intern-contracts/upload/<int:contract_id>'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_intern_contract_upload(self, contract_id, **post):
        partner = request.env.user.partner_id
        Contract = request.env['intern.contract']
        contract = Contract.search([('id', '=', contract_id), ('intern_id.partner_id', '=', partner.id)], limit=1)
        if not contract:
            return request.not_found()

        file = post.get('contract_file')
        if file and hasattr(file, 'filename'):
            binary_data = file.read()
            encoded_data = base64.b64encode(binary_data).decode('utf-8')  # als String speichern
            contract.write({
                'upload': encoded_data,
                'upload_filename': file.filename,
                'state': 'uploaded'
            })
        return request.redirect('/my/intern-contracts/%s' % contract_id)

    @http.route(['/my/intern-contracts/sign/<int:contract_id>'], type='http', auth='user', website=True)
    def portal_intern_contract_sign(self, contract_id, **kwargs):
        Contract = request.env['intern.contract']
        partner = request.env.user.partner_id
        contract = Contract.search([('id', '=', contract_id), ('intern_id.partner_id', '=', partner.id)], limit=1)
        if not contract or not contract.sign_request_id:
            return request.redirect('/my/intern-contracts/%s' % contract_id)

        request_item = contract.sign_request_id.request_item_ids.filtered(lambda r: r.partner_id.id == partner.id)[:1]
        if request_item and request_item.access_token:
            return request.redirect('/sign/document/%s/%s' % (contract.sign_request_id.id, request_item.access_token))
        return request.redirect('/my/intern-contracts/%s' % contract_id)

    @http.route(['/my/intern-contracts/upload_new'], type='http', auth='user', methods=['POST'], website=True,
                csrf=True)
    def portal_intern_contract_upload_new(self, **post):
        _logger.info(">>> upload_new aufgerufen, post keys: %s", list(post.keys()))
        partner = request.env.user.partner_id

        # passenden Praktikanten bestimmen
        intern = request.env['intern.intern'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        if not intern:
            return request.not_found()

        file = post.get('contract_file')
        if not file or not hasattr(file, 'filename'):
            return request.redirect('/my/intern-contracts')

        # Datei lesen und Base64 kodieren
        binary_data = file.read()
        encoded_data = base64.b64encode(binary_data).decode('utf-8')

        # Einfachen Vertrag anlegen – ohne SignRequest etc.
        contract = request.env['intern.contract'].sudo().create({
            'name': file.filename or 'Eigener Vertrag (Schule)',
            'intern_id': intern.id,
            'upload': encoded_data,
            'upload_filename': file.filename,
            'state': 'uploaded',
            'note': 'Vom Praktikanten manuell hochgeladen (z.B. Schulvertrag)',
        })

        # Admin ermitteln
        try:
            admin_user = request.env.ref('base.user_admin').sudo()
        except ValueError:
            admin_user = request.env.ref('base.user_root').sudo()

        contract.sudo().write({'responsible_id': admin_user.id})
        admin_partner_id = admin_user.partner_id.id

        # Admin-Link: direkt ins Backend, absolut
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        admin_url = f"{base_url}/web#id={contract.id}&model=intern.contract&view_type=form"

        body_html = f"""
            <p>Der/die Praktikant:in <strong>{partner.name}</strong>
            hat einen eigenen Vertrag hochgeladen (z. B. von der Schule).</p>
            <p>
              <a href="{admin_url}" target="_blank"
                 style="background:#2c7be5;color:#fff;padding:8px 12px;
                 text-decoration:none;border-radius:4px;">
                 Verträge im Backend ansehen
              </a>
            </p>
        """

        contract.sudo().message_subscribe(partner_ids=[admin_partner_id])
        contract.sudo().message_post(
            subject="Eigener Vertrag vom Praktikanten hochgeladen",
            body=body_html,
            partner_ids=[admin_partner_id],
            subtype_xmlid="mail.mt_note",
        )

        # Optionale Aktivität für Admin
        request.env['mail.activity'].sudo().create({
            'res_model_id': request.env['ir.model']._get_id('intern.contract'),
            'res_id': contract.id,
            'activity_type_id': request.env.ref('mail.mail_activity_data_todo').id,
            'summary': 'Praktikant:in hat eigenen Vertrag hochgeladen',
            'user_id': admin_user.id,
        })

        return request.redirect(f"/my/intern-contracts/{contract.id}")