# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp.exceptions import Warning
from openerp import models, fields, api, _


class account_check_action(models.TransientModel):
    _name = 'account.check.action'

    @api.model
    def _get_company_id(self):
        active_ids = self._context.get('active_ids', [])
        checks = self.env['account.check'].browse(active_ids)
        company_ids = [x.company_id.id for x in checks]
        if len(set(company_ids)) > 1:
            raise Warning(_('All checks must be from the same company!'))
        return self.env['res.company'].search(
            [('id', 'in', company_ids)], limit=1)

    journal_id = fields.Many2one(
        'account.journal', 'Journal',
        domain=[('type', 'in', ['cash', 'bank'])])
    date = fields.Date(
        'Date', required=True, default=fields.Date.context_today)
    action_type = fields.Char(
        'Action type passed on the context', required=True)
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=_get_company_id
    )

    def action_confirm(self, cr, uid, ids, context=None):
        check_obj = self.pool.get('account.check')
        move_line_obj = self.pool.get('account.move.line')
        wizard = self.browse(cr, uid, ids[0], context=context)
        context['company_id'] = wizard.company_id.id

        # used to get correct ir properties
        context['force_company'] = wizard.company_id.id

        period_id = self.pool.get('account.period').find(
            cr, uid, wizard.date, context=context)[0]
        if context is None:
            context = {}

        record_ids = context.get('active_ids', [])
        for check in check_obj.browse(cr, uid, record_ids, context=context):
            # state controls
            if wizard.action_type == 'deposit':
                if check.type == 'third':
                    if check.state != 'holding':
                        raise Warning(
                            _('The selected checks must be in holding state.'))
                else:   # issue
                    raise Warning(_('You can not deposit a Issue Check.'))
            elif wizard.action_type == 'debit':
                if check.type == 'issue':
                    if check.state != 'handed':
                        raise Warning(
                            _('The selected checks must be in handed state.'))
                else:   # third
                    raise Warning(_('You can not debit a Third Check.'))
            elif wizard.action_type == 'return':
                if check.type == 'third':
                    if check.state != 'holding':
                        raise Warning(
                            _('The selected checks must be in holding state.'))
                else:   # issue
                    raise Warning(_('You can not return a Issue Check.'))

            check_vals = {}
            debit_date_due = False
            credit_date_due = False

            if wizard.action_type == 'deposit':
                ref = _('Deposit Check Nr. ')
                check_move_field = 'deposit_account_move_id'
                journal = wizard.journal_id
                debit_account_id = journal.default_debit_account_id.id
                partner = check.source_partner_id.id,
                credit_account_id = check.voucher_id.journal_id.default_credit_account_id.id
                signal = 'holding_deposited'
            elif wizard.action_type == 'debit':
                ref = _('Debit Check Nr. ')
                check_move_field = 'debit_account_move_id'
                journal = check.checkbook_id.debit_journal_id
                partner = check.destiny_partner_id.id
                credit_account_id = journal.default_debit_account_id.id
                debit_account_id = check.voucher_id.journal_id.default_credit_account_id.id
                signal = 'handed_debited'
            elif wizard.action_type == 'return': # return back to customer
                ref = _('Return Check Nr. ')
                check_move_field = 'return_account_move_id'
                journal = check.voucher_id.journal_id
                debit_account_id = check.source_partner_id.property_account_receivable.id
                partner = check.source_partner_id.id,
                credit_account_id = check.voucher_id.journal_id.default_credit_account_id.id
                credit_date_due = check.payment_date
                signal = 'holding_returned'

            name = self.pool.get('ir.sequence').next_by_id(
                cr, uid, journal.sequence_id.id, context=context)
            ref += check.name
            move_id = self.pool.get('account.move').create(cr, uid, {
                'name': name,
                'journal_id': journal.id,
                'period_id': period_id,
                'date': wizard.date,
                'ref':  ref,
            })
            move_line_obj.create(cr, uid, {
                'name': name,
                'account_id': debit_account_id,
                'partner_id': partner,
                'move_id': move_id,
                'debit': check.company_currency_amount or check.amount,
                'amount_currency': check.company_currency_amount and check.amount or False,
                'ref': ref,
                'date_maturity': debit_date_due or False,
            })
            move_line_obj.create(cr, uid, {
                'name': name,
                'account_id': credit_account_id,
                'partner_id': partner,
                'move_id': move_id,
                'credit': check.company_currency_amount or check.amount,
                'amount_currency': check.company_currency_amount and -1 * check.amount or False,
                'ref': ref,
                'date_maturity': credit_date_due or False,
            })

            check_vals[check_move_field] = move_id
            check.write(check_vals)
            check.signal_workflow(signal)
        self.pool.get('account.move').write(
            cr, uid, [move_id], {'state': 'posted', }, context=context)

        return {}
