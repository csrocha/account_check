# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging
import openupgradelib
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info('Migrating account_check from version %s' % version)

    cr.execute("""
INSERT INTO account_check (
 id, create_uid, create_date, write_date, write_uid,
 state, number, issue_date, amount, company_id, user_id, voucher_id,
 clearing, bank_id, vat, type,
 source_partner_id, destiny_partner_id,
 payment_date
)
SELECT id, create_uid, create_date, write_date, write_uid,
 state, CAST(number AS INT), date, amount, company_id, user_id, voucher_id,
 clearing, bank_id, vat, 'third',
 source_partner_id, destiny_partner_id,
 clearing_date
FROM account_third_check
        """)
    pass
