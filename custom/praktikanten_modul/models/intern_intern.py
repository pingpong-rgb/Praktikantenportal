from odoo import models, fields, api
from odoo.exceptions import UserError

class InternIntern(models.Model):
    _name = 'intern.intern'
    _description = 'Praktikant/in'

    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='E-Mail')
    phone = fields.Char(string='Telefon')
    start_date = fields.Date(string='Startdatum')
    end_date = fields.Date(string='Enddatum')
    company_id = fields.Many2one(
        'res.company',
        string='Unternehmen',
        required=True,
        default=lambda self: self.env.company
    )
    active = fields.Boolean(string='Aktiv', default=True)
    partner_id = fields.Many2one('res.partner', string='Kontakt', ondelete='cascade')

    def action_send_invitation(self):
        PortalWizard = self.env['portal.wizard']
        PortalWizardUser = self.env['portal.wizard.user']

        for intern in self:
            if not intern.email:
                raise UserError("Bitte zuerst eine E-Mail-Adresse eintragen.")

            # Partner suchen oder anlegen
            partner = intern.partner_id or self.env['res.partner'].search([('email', '=', intern.email)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': intern.name,
                    'email': intern.email,
                    'company_id': intern.company_id.id,
                    'lang': self.env.user.lang or 'de_DE',
                })
            intern.partner_id = partner

            # Sprache & Signup-Link sicherstellen
            if not partner.lang:
                partner.lang = self.env.user.lang or 'de_DE'
            partner.signup_prepare()  # erzeugt signup_token & URL für den Partner

            # Einen Wizard + Wizard-User anlegen (Kontext für das Template)
            wizard = self.env['portal.wizard'].create({})
            wiz_user = self.env['portal.wizard.user'].create({
                'wizard_id': wizard.id,
                'partner_id': partner.id,
                'email': partner.email,
            })

            # Portal-Standardvorlage GEGEN den Wizard-User senden
            template = self.env.ref('portal.mail_template_data_portal_welcome')
            template.send_mail(wiz_user.id, force_send=True, raise_exception=True)

        return True