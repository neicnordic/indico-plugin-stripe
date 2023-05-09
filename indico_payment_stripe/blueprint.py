# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.blueprint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The plugin blueprint.

"""
from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_stripe.controllers import RHStripeIntent, RHStripeReturn


blueprint = IndicoPluginBlueprint(
    'payment_stripe',
    __name__,
    url_prefix=(
        '/event/<int:event_id>/registrations/'
        '<int:reg_form_id>/payment/response/stripe'
    )
)

blueprint.add_url_rule('/intent', 'intent', RHStripeIntent, methods=['POST'])
blueprint.add_url_rule('/return', 'return', RHStripeReturn)
