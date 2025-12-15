# custom/praktikanten_modul_vertraege/models/sign_request_hook.py
from odoo import models, fields, api

class SignRequest(models.Model):
    _inherit = 'sign.request'

    intern_contract_id = fields.Many2one('intern.contract', string='Praktikumsvertrag', readonly=True)

    # Hilfsfunktion: finde zugehörigen Praktikanten
    def _get_related_intern(self):
        self.ensure_one()
        partners = self.request_item_ids.mapped('partner_id')
        if not partners:
            return False
        return self.env['intern.intern'].sudo().search([('partner_id', 'in', partners.ids)], limit=1)

    # Erzeuge/aktualisiere Vertrag passend zum Request
    def _ensure_intern_contract(self):
        self.ensure_one()
        intern = self._get_related_intern()
        if not intern:
            return False

        # Ableiten des Status
        state_map = {
            'completed': 'signed',
            'in_progress': 'awaiting',
            'to_sign': 'awaiting',
            'sent': 'awaiting',
            'canceled': 'cancel',
        }
        mapped_state = state_map.get(self.state, 'draft')

        # Falls schon verknüpft -> aktualisieren
        if self.intern_contract_id:
            self.intern_contract_id.write({
                'name': self.subject or self.reference or self.intern_contract_id.name or "Praktikumsvertrag",
                'intern_id': intern.id,
                'sign_request_id': self.id,
                'state': mapped_state,
                'signed_date': self.completion_date or self.intern_contract_id.signed_date,
            })
            return self.intern_contract_id

        # Neu anlegen
        contract = self.env['intern.contract'].sudo().create({
            'name': self.subject or self.reference or intern.name or "Praktikumsvertrag",
            'intern_id': intern.id,
            'sign_request_id': self.id,
            'state': mapped_state,
            'signed_date': self.completion_date or False,
        })
        self.intern_contract_id = contract.id
        return contract

    # Hooks
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for req in records:
            intern = req._get_related_intern()
            if intern:
                req._ensure_intern_contract()
        return records

    def write(self, vals):
        res = super().write(vals)
        for req in self:
            if req._get_related_intern():
                req._ensure_intern_contract()
        return res
