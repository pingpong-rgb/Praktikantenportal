# -*- coding: utf-8 -*-
{
    'name': 'Praktikantenmodul',
    'version': '1.1.4',
    'summary': 'Verwaltung von Praktikant:innen, Aufgaben, Zeiten und Wochenberichten',
    'description': """
Odoo-Modul für Ausbildungsbetriebe und Unternehmen zur effizienten Verwaltung von Praktikant:innen.
Enthält Funktionen für Aufgabenmanagement, Zeiterfassung, Wochenberichte und Portalzugang.
""",
    'author': 'fiaTG',
    'website': 'https://github.com/fiaTG/praktikanten_modul',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'project',
        'hr',
        'hr_timesheet',
        'portal',
        'mail',
        'sign',
    ],
    'data': [
        'security/intern_security.xml',            # Gruppen müssen zuerst geladen werden
        'security/intern_onboarding_rules.xml',    # dann können Regeln geladen werden
        'security/ir.model.access.csv',
        'security/intern_intern_rules.xml',
        'security/intern_onboarding_access.xml',
        'views/intern_intern_views.xml',
        'views/intern_onboarding_views.xml',
        'views/intern_portal_onboarding_templates.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}