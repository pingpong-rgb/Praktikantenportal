# custom/praktikanten_modul_vertraege/models/intern_contract.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InternContract(models.Model):
    _name = 'intern.contract'
    _description = 'Praktikumsvertrag'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Grunddaten
    name = fields.Char(string='Bezeichnung', required=True, tracking=True, default="Praktikumsvertrag")
    intern_id = fields.Many2one('intern.intern', string='Praktikant/in', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='intern_id.company_id', store=True, readonly=True)

    # Statusfelder
    state = fields.Selection([
        ('draft', 'Entwurf'),
        ('awaiting', 'Warten auf Unterschrift'),
        ('signed', 'Unterschrieben'),
        ('uploaded', 'Hochgeladen (extern)'),
        ('cancel', 'Abgebrochen'),
    ], string='Status', default='draft', tracking=True)

    upload = fields.Binary(attachment=True, string='Eigener Vertrag (PDF)')
    upload_filename = fields.Char(string='Dateiname')

    # Signaturintegration
    sign_request_id = fields.Many2one('sign.request', string='Sign-Anfrage', readonly=True)
    # Hinweis: sign_status ist nur das Related auf die Request-State
    sign_status = fields.Selection(related='sign_request_id.state', store=True, readonly=True, string='Sign Status')
    signed_date = fields.Datetime(string='Unterschrieben am', readonly=True)

    responsible_id = fields.Many2one('res.users', string='Verantwortlich', default=lambda self: self.env.user, tracking=True)
    note = fields.Text(string='Notiz')

    # --- Manuelle Status-Aktionen (optional) ---
    def action_mark_awaiting(self):
        self.write({'state': 'awaiting'})

    def action_mark_signed(self):
        self.write({'state': 'signed', 'signed_date': fields.Datetime.now()})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_open_sign(self):
        self.ensure_one()
        if not self.sign_request_id:
            raise UserError(_("Keine Sign-Anfrage verknüpft."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sign.request',
            'res_id': self.sign_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # --- Backfill-Utility: vorhandene Sign Requests in Verträge spiegeln ---
    @api.model
    def action_sync_from_sign(self):
        """Erzeuge fehlende intern.contract aus existierenden sign.request, falls ein Praktikanten-Partner beteiligt ist."""
        SignRequest = self.env['sign.request'].sudo()
        requests = SignRequest.search([])

        created = 0
        for req in requests:
            if req._get_related_intern() and not req.intern_contract_id:
                req._ensure_intern_contract()
                created += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sync abgeschlossen"),
                'message': _("%s Vertrag/Verträge aus Sign erzeugt.", created),
                'sticky': False,
                'type': 'success',
            }
        }