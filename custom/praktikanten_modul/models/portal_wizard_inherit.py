from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class PortalWizardUser(models.TransientModel):
    _inherit = "portal.wizard.user"

    def action_apply(self):
        """Hook after portal invitation is applied."""
        _logger.warning("Portal Wizard action triggered for partner %s", self.partner_id.id)
        result = super().action_apply()

        for wizard_user in self:
            partner = wizard_user.partner_id
            if not partner:
                continue

            # Hole den User, der durch die Einladung erstellt wurde
            user = partner.user_ids[:1]
            if not user:
                continue

            # >>> Hier Gruppen hinzufügen <<<
            # XML‑IDs der Gruppen holen
            portal_group = self.env.ref('base.group_portal')
            intern_portal_group = self.env.ref('praktikanten_modul.group_intern_portal')
            contract_portal_group = self.env.ref('praktikanten_modul_vertraege.group_intern_contract_portal')

            # Liste der Gruppen, die hinzugefügt werden sollen
            for group in (portal_group, intern_portal_group, contract_portal_group):
                # Prüfen, ob die Gruppe existiert und der User noch nicht Mitglied ist
                if group and group not in user.groups_id:
                    user.groups_id = [(4, group.id)]  # (4, id) fügt die Gruppe hinzu

            # Optional: Employee anlegen (bestehender Code)
            wizard_user._create_employee_for_user(user)

        return result

    def _create_employee_for_user(self, user):
        """Hilfsfunktion, erstellt Employee falls Praktikant."""
        intern = self.env['intern.intern'].sudo().search([
            ('partner_id', '=', user.partner_id.id)
        ], limit=1)

        if not intern:
            return

        employee_obj = self.env['hr.employee'].sudo()
        employee = employee_obj.search([('user_id', '=', user.id)], limit=1)

        if not employee:
            employee_obj.create({
                'name': intern.name or user.name,
                'user_id': user.id,
                'work_email': intern.email or user.email or user.partner_id.email,
                'mobile_phone': intern.phone or user.partner_id.phone,
                'company_id': intern.company_id.id if intern.company_id else (user.company_id.id if user.company_id else self.env.company.id),
                'job_title': 'Praktikant/in',
            })
            _logger.warning("✅ Employee automatically created for intern user %s (%s)", user.name, user.id)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        HrEmployee = self.env['hr.employee'].sudo()
        Intern = self.env['intern.intern'].sudo()

        # Hole die Gruppen-Referenzen nur einmal
        intern_portal_group = self.env.ref('praktikanten_modul.group_intern_portal', raise_if_not_found=False)
        contract_portal_group = self.env.ref('praktikanten_modul_vertraege.group_intern_contract_portal', raise_if_not_found=False)

        for user in users:
            partner = user.partner_id
            if not partner:
                continue

            intern = Intern.search([('partner_id', '=', partner.id)], limit=1)
            if not intern:
                continue

            # Wenn ein Praktikant gefunden wurde, füge die Gruppen hinzu
            commands = []
            if intern_portal_group and intern_portal_group not in user.groups_id:
                commands.append((4, intern_portal_group.id))
            if contract_portal_group and contract_portal_group not in user.groups_id:
                commands.append((4, contract_portal_group.id))
            if commands:
                user.write({'groups_id': commands})

            # bestehende Employee-Logik
            if not HrEmployee.search([('user_id', '=', user.id)], limit=1):
                company = intern.company_id or user.company_id or self.env.company
                HrEmployee.create({
                    'name': intern.name or partner.name or user.name,
                    'user_id': user.id,
                    'work_email': intern.email or user.email or partner.email,
                    'mobile_phone': intern.phone or partner.mobile or partner.phone,
                    'company_id': company.id if company else False,
                    'job_title': 'Praktikant/in',
                })
                _logger.warning("✅ Employee created via res.users.create() for intern %s", intern.name)
        return users