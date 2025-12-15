from odoo import models, fields

class InternOnboarding(models.Model):
    _name = "intern.onboarding"
    _description = "Onboarding Inhalte für Praktikanten"
    _order = "sequence, name"

    name = fields.Char("Titel", required=True)
    description = fields.Text("Beschreibung")
    file = fields.Binary("Datei", attachment=True)
    file_name = fields.Char("Dateiname")
    link_url = fields.Char("Web-Link")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)