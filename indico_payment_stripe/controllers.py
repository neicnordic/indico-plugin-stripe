# -*- coding: utf-8 -*-
"""
    indico_payment_stripe.controllers
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Controllers used by the plugin.

"""
from __future__ import unicode_literals

import stripe
from flask import redirect, request, jsonify
from flask_pluginengine import current_plugin
from stripe import error as err
from werkzeug.exceptions import BadRequest

from indico.modules.events.payment.models.transactions import TransactionAction
from indico.modules.events.payment.util import register_transaction
from indico.modules.events.registration.models.registrations import Registration
from indico.web.flask.util import url_for
from indico.web.rh import RH

from .utils import _, conv_to_stripe_amount, conv_from_stripe_amount


__all__ = ['RHStripeIntent', 'RHStripeReturn']


STRIPE_TRX_ACTION_MAP = {
    'canceled': TransactionAction.cancel,
    'processing': TransactionAction.pending,
    'requires_action': TransactionAction.pending,
    'requires_capture': TransactionAction.pending,
    'requires_confirmation': TransactionAction.pending,
    'requires_payment_method': TransactionAction.pending,
    'succeeded': TransactionAction.complete,
}


class RHStripeIntent(RH):

    CSRF_ENABLED = False

    def _get_event_settings(self, settings_name):
        event_settings = current_plugin.event_settings
        return event_settings.get(
            self.registration.registration_form.event,
            settings_name
        )

    def _process_args(self):
        self.token = request.args['token']
        self.registration = Registration.query.filter_by(uuid=self.token).first()
        if not self.registration:
            raise BadRequest

    def _process(self):
        description = self._get_event_settings('description')
        use_event_api_keys = self._get_event_settings('use_event_api_keys')
        sec_key = (
            self._get_event_settings('sec_key')
            if use_event_api_keys else
            current_plugin.settings.get('sec_key')
        )

        try:
            intent = stripe.PaymentIntent.create(
                api_key=sec_key,
                amount=conv_to_stripe_amount(
                    self.registration.price,
                    self.registration.currency
                ),
                currency=self.registration.currency.lower(),
                description=description,
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            return jsonify({
                'clientSecret': intent['client_secret']
            })
        except Exception as e:
            return jsonify(error=str(e)), 403


class RHStripeReturn(RH):

    CSRF_ENABLED = False

    def _get_event_settings(self, settings_name):
        event_settings = current_plugin.event_settings
        return event_settings.get(
            self.registration.registration_form.event,
            settings_name
        )

    def _process_args(self):
        self.token = request.args['token']
        self.payment_intent = request.args['payment_intent']
        self.registration = Registration.query.filter_by(uuid=self.token).first()
        if not self.registration:
           raise BadRequest

    def _process(self):
        description = self._get_event_settings('description')
        use_event_api_keys = self._get_event_settings('use_event_api_keys')
        sec_key = (
            self._get_event_settings('sec_key')
            if use_event_api_keys else
            current_plugin.settings.get('sec_key')
        )

        try:
            intent = stripe.PaymentIntent.retrieve(
                self.payment_intent,
                api_key=sec_key,
            )
        except Exception as e:
            return jsonify(error=str(e)), 403

        register_transaction(
            registration=self.registration,
            amount=conv_from_stripe_amount(
                intent['amount_received'],
                intent['currency']
            ),
            currency=intent['currency'],
            action=STRIPE_TRX_ACTION_MAP[intent['status']],
            provider='stripe',
        )

        reg_url = url_for(
            'event_registration.display_regform',
            self.registration.locator.registrant
        )

        return redirect(reg_url)
