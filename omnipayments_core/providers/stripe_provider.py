"""
Stripe Payment Provider Wrapper
Wraps existing Stripe service to conform to BasePaymentProvider interface
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from .base import BasePaymentProvider
import stripe as stripe_lib
from stripe import _error as stripe_error
import logging

logger = logging.getLogger(__name__)


class StripeProvider(BasePaymentProvider):
    """
    Stripe payment provider implementation.
    Wraps the existing StripeService to provide a consistent interface.
    """
    
    provider_name = "stripe"
    
    def __init__(self, config: Dict[str, Any]):
        self.secret_key = None
        self.publishable_key = None
        self.webhook_secret = None
        super().__init__(config)
        
        # Initialize Stripe
        stripe_lib.api_key = self.secret_key
    
    def validate_config(self):
        """Validate Stripe configuration."""
        required_fields = ['secret_key', 'publishable_key']
        
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Stripe provider requires '{field}' in configuration")
        
        self.secret_key = self.config['secret_key']
        self.publishable_key = self.config['publishable_key']
        self.webhook_secret = self.config.get('webhook_secret')
    
    def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe Checkout session."""
        try:
            session_params = {
                'mode': 'subscription',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'client_reference_id': user_id,
                'metadata': {
                    'user_id': user_id,
                    'plan_id': plan_id,
                    **(metadata or {})
                }
            }
            
            # If price_id is provided in metadata, use it
            price_id = metadata.get('stripe_price_id') if metadata else None
            if price_id:
                session_params['line_items'] = [{
                    'price': price_id,
                    'quantity': 1,
                }]
            
            session = stripe_lib.checkout.Session.create(**session_params)
            
            return {
                'session_id': session.id,
                'session_url': session.url,
                'provider': self.provider_name,
                'publishable_key': self.publishable_key,
                'metadata': session_params['metadata']
            }
        
        except stripe_error.StripeError as e:
            logger.error(f"Stripe checkout session creation failed: {str(e)}")
            raise
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe subscription."""
        try:
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'metadata': metadata or {}
            }
            
            if trial_days > 0:
                subscription_params['trial_period_days'] = trial_days
            
            subscription = stripe_lib.Subscription.create(**subscription_params)
            
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(
                    subscription.current_period_start,
                    tz=timezone.utc
                ),
                'current_period_end': datetime.fromtimestamp(
                    subscription.current_period_end,
                    tz=timezone.utc
                ),
            }
        
        except stripe_error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {str(e)}")
            raise
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Cancel Stripe subscription."""
        try:
            if immediate:
                subscription = stripe_lib.Subscription.delete(subscription_id)
            else:
                subscription = stripe_lib.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            return {
                'subscription_id': subscription_id,
                'status': subscription.status,
                'cancelled_at': datetime.now(tz=timezone.utc),
            }
        
        except stripe_error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {str(e)}")
            raise
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify Stripe webhook signature."""
        try:
            stripe_lib.Webhook.construct_event(
                payload, signature, secret
            )
            return True
        except stripe_error.SignatureVerificationError:
            return False
        except Exception as e:
            logger.error(f"Webhook verification error: {str(e)}")
            return False
    
    def process_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Stripe webhook events."""
        logger.info(f"Processing Stripe webhook: {event_type}")
        
        processed_data = {
            'provider': self.provider_name,
            'event_type': event_type,
        }
        
        # Map Stripe events
        if event_type == 'checkout.session.completed':
            processed_data.update({
                'session_id': event_data.get('id'),
                'customer_id': event_data.get('customer'),
                'subscription_id': event_data.get('subscription'),
                'metadata': event_data.get('metadata', {}),
            })
        
        elif event_type == 'invoice.payment_succeeded':
            processed_data.update({
                'payment_status': 'succeeded',
                'amount': Decimal(event_data.get('amount_paid', 0)) / 100,
                'currency': event_data.get('currency', '').upper(),
                'subscription_id': event_data.get('subscription'),
                'customer_id': event_data.get('customer'),
                'invoice_id': event_data.get('id'),
                'billing_reason': event_data.get('billing_reason'),
            })
        
        elif event_type == 'invoice.payment_failed':
            processed_data.update({
                'payment_status': 'failed',
                'subscription_id': event_data.get('subscription'),
                'customer_id': event_data.get('customer'),
            })
        
        return {
            'status': 'success',
            'event_type': event_type,
            'processed_data': processed_data
        }
    
    def get_payment_status(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """Get Stripe payment intent status."""
        try:
            payment = stripe_lib.PaymentIntent.retrieve(payment_id)
            
            return {
                'payment_id': payment_id,
                'status': payment.status,
                'amount': Decimal(payment.amount) / 100,
                'currency': payment.currency.upper(),
            }
        
        except stripe_error.StripeError as e:
            logger.error(f"Failed to get payment status: {str(e)}")
            raise
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Refund a Stripe payment."""
        try:
            refund_params = {'payment_intent': payment_id}
            
            if amount:
                refund_params['amount'] = int(amount * 100)
            
            refund = stripe_lib.Refund.create(**refund_params)
            
            return {
                'refund_id': refund.id,
                'status': refund.status,
                'amount': Decimal(refund.amount) / 100,
            }
        
        except stripe_error.StripeError as e:
            logger.error(f"Refund failed: {str(e)}")
            raise
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Stripe customer."""
        try:
            customer = stripe_lib.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            
            return {
                'customer_id': customer.id,
                'email': email,
            }
        
        except stripe_error.StripeError as e:
            logger.error(f"Customer creation failed: {str(e)}")
            raise
    
    def supports_subscriptions(self) -> bool:
        """Stripe supports subscriptions."""
        return True
    
    def supports_refunds(self) -> bool:
        """Stripe supports refunds."""
        return True
    
    def get_supported_currencies(self) -> list:
        """Stripe supports 135+ currencies."""
        return ['USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'KHR', 'THB', 'VND', 'SGD']  # Common ones
