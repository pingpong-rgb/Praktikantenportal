from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from datetime import date, timedelta, datetime
import calendar

class PortalTimesheetController(http.Controller):

    @http.route(['/my/task/<int:task_id>/timesheet'], type='http', auth='user', website=True)
    def portal_task_timesheet_form(self, task_id, **kw):
        task = request.env['project.task'].sudo().browse(task_id)
        if request.env.user.partner_id not in task.message_partner_ids:
            return request.redirect('/my/tasks')
        if not task.exists():
            raise MissingError("Task not found")

        partner = request.env.user.partner_id
        # Access allowed if partner assigned to task or project
        if partner not in task.project_id.message_partner_ids and partner != task.partner_id:
            raise AccessError("No access to this task")

        values = {
            'task': task,
            'page_name': 'task_timesheet',
        }
        return request.render('praktikanten_modul_vertraege.portal_task_timesheet_form', values)


    @http.route(['/my/task/<int:task_id>/timesheet/submit'], type='http', auth='user', website=True, methods=['POST'])
    def portal_task_timesheet_submit(self, task_id, **post):
        task = request.env['project.task'].sudo().browse(task_id)
        if not task.exists():
            raise MissingError("Task not found")

        partner = request.env.user.partner_id
        if partner not in task.project_id.message_partner_ids and partner != task.partner_id:
            raise AccessError("No access to this task")

        description = post.get('description', '').strip()
        hours = float(post.get('hours', 0))

        if not description or hours <= 0:
            return request.redirect(f'/my/task/{task_id}/timesheet?error=1')

        # create timesheet entry
        request.env['account.analytic.line'].sudo().create({
            'name': description,
            'unit_amount': hours,
            'task_id': task.id,
            'project_id': task.project_id.id,
            'user_id': request.env.user.id,
            'partner_id': partner.id,
            'date': fields.Date.today(),
            'is_timesheet': True,
        })

        return request.redirect(f'/my/task/{task_id}?submitted=1')


    @http.route(['/my/wochenberichte'], type='http', auth='user', website=True)
    def portal_weekly_reports_list(self, **kw):
        """Zeigt Übersicht aller Wochen mit vorhandenen Timesheets."""
        user = request.env.user
        timesheets = request.env['account.analytic.line'].sudo().search([
            ('user_id', '=', user.id),
            ('is_timesheet', '=', True),
        ], order='date desc')

        # Gruppieren nach Kalenderwoche
        weeks = {}
        for ts in timesheets:
            year, week, _ = ts.date.isocalendar()
            key = (year, week)
            weeks.setdefault(key, []).append(ts)

        # Sortieren: neueste zuerst
        sorted_weeks = sorted(weeks.items(), reverse=True)

        values = {
            'weeks': [
                {
                    'year': year,
                    'week': week,
                    'start_date': date.fromisocalendar(year, week, 1),
                    'end_date': date.fromisocalendar(year, week, 7),
                    'timesheet_count': len(ts_list),
                }
                for (year, week), ts_list in sorted_weeks
            ],
            'page_name': 'wochenberichte_list',
        }

        return request.render('praktikanten_modul_vertraege.portal_weekly_reports_list', values)

    @http.route(['/my/wochenberichte/<int:year>/<int:week>'], type='http', auth='user', website=True)
    def portal_weekly_report_pdf(self, year, week, **kw):
        """Generiert den PDF-Wochenbericht für eine bestimmte Kalenderwoche."""
        user = request.env.user
        start_of_week = date.fromisocalendar(year, week, 1)
        end_of_week = date.fromisocalendar(year, week, 7)

        timesheets = request.env['account.analytic.line'].sudo().search([
            ('user_id', '=', user.id),
            ('date', '>=', start_of_week),
            ('date', '<=', end_of_week),
            ('is_timesheet', '=', True),
        ], order='date asc')

        if not timesheets:
            return request.redirect('/my/wochenberichte')

        report = request.env['ir.actions.report'].sudo()
        pdf_content, _ = report._render_qweb_pdf(
            'hr_timesheet.report_timesheet',
            res_ids=timesheets.ids
        )

        pdf_http_headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename="Wochenbericht_{year}_KW{week}.pdf"')
        ]
        return request.make_response(pdf_content, headers=pdf_http_headers)


    @http.route(['/my/timesheets'], type='http', auth='user', website=True)
    def portal_my_timesheets(self, **kw):
        """Zeigt alle eigenen Timesheets des Portal-Users."""
        user = request.env.user
        Timesheet = request.env['account.analytic.line'].sudo()

        # Nur eigene Timesheets anzeigen
        timesheets = Timesheet.search([
            ('user_id', '=', user.id),
            ('is_timesheet', '=', True),
        ], order='date desc')

        values = {
            'timesheets': timesheets,
            'page_name': 'my_timesheets',
        }
        return request.render('praktikanten_modul_vertraege.portal_my_timesheets', values)
