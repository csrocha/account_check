# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging
from openerp import pooler, SUPERUSER_ID
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        'Running post migrate of account_check from version %s' % version)

