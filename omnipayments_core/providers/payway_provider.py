"""
PayWay Payment Provider
Cambodia's eCommerce Checkout solution - supports multiple payment methods

Supports:
- Credit/Debit Cards
- ABA Pay
- KHQR (QR code payments)
- WeChat Pay
- Alipay
- Google Pay
"""
import requests
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from .base import BasePaymentProvider
import logging

logger = logging.getLogger(__name__)


class PayWayProvider(BasePaymentProvider):
    """
    PayWay eCommerce Checkout payment provider implementation.
    
    PayWay is Cambodia's eCommerce payment platform operated by ABA Bank.
    Supports multiple payment methods via a unified checkout interface.
    
    Configuration required:
    - merchant_id: Your PayWay merchant ID
    - private_key: Private key for generating request signatures/hashes
    - public_key: (Optional) Public key for webhook verification
    - sandbox: Boolean - use sandbox (True) or production (False)
    - return_url: Optional - URL to receive payment status callbacks (whitelisted in merchant profile)
    """
    
    provider_name = "payway"
    
    # PayWay API endpoints
    PRODUCTION_URL = "https://api.payway.com.kh"
    SANDBOX_URL = "https://api-sandbox.payway.com.kh"
    
    def __init__(self, config: Dict[str, Any]):
        self.merchant_id = None
        self.private_key = None
        self.public_key = None
        self.api_url = None
        self.is_sandbox = None
        self.return_url = None
        super().__init__(config)
    
    def validate_config(self):
        """Validate PayWay configuration."""
        required_fields = ['merchant_id', 'private_key']
        
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"PayWay provider requires '{field}' in configuration")
        
        self.merchant_id = self.config['merchant_id']
        self.private_key = self.config['private_key']
        self.public_key = self.config.get('public_key')
        self.is_sandbox = self.config.get('sandbox', True)
        self.api_url = self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL
        self.return_url = self.config.get('return_url')
    
    def _generate_signature(self, payload: str) -> str:
        """
        Generate hash signature for PayWay API requests.
        
        PayWay uses hash-based authentication where request parameters
        are hashed using the merchant's private key.
        """
        signature = hmac.new(
            self.private_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request to PayWay."""
        url = f"{self.api_url}{endpoint}"
        
        # Prepare payload
        payload = json.dumps(data) if data else ""
        
        # Generate signature
        signature = self._generate_signature(payload)
        
        headers = {
            'Content-Type': 'application/json',
            'X-PayWay-Merchant-ID': self.merchant_id,
            'X-PayWay-API-Key': self.api_key,
            'X-PayWay-Signature': signature,
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"PayWay API request failed: {str(e)}")
            raise
    
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
        """
        Create a PayWay eCommerce Checkout session.
        
        PayWay returns a checkout modal/HTML that displays multiple payment methods
        for the customer to choose from.
        
        Returns:
            {
                'session_id': str,  # Transaction ID from PayWay
                'checkout_html': str,  # HTML/iframe to render checkout
                'provider': str,
                'metadata': dict
            }
        """
        if currency.upper() not in ['USD', 'KHR']:
            raise ValueError(f"PayWay only supports USD and KHR currencies, got {currency}")
        
        # Convert amount to smallest unit
        # USD: cents (multiply by 100)
        # KHR: riel (no decimal places)
        if currency.upper() == 'USD':
            amount_minor = int(amount * 100)
        else:
            amount_minor = int(amount)
        
        # Create transaction request
        transaction_data = {
            'merchant_id': self.merchant_id,
            'tran_id': f"tran_{user_id}_{plan_id}_{int(datetime.now(tz=timezone.utc).timestamp())}",
            'amount': amount_minor,
            'currency': currency.upper(),
            'description': f"Subscription to plan {plan_id}",
            'items': [
                {
                    'name': f"Plan {plan_id}",
                    'quantity': 1,
                    'price': amount_minor,
                }
            ],
            'billing': {
                'fname': metadata.get('first_name', 'Customer') if metadata else 'Customer',
                'lname': metadata.get('last_name', '') if metadata else '',
                'email': metadata.get('email', '') if metadata else '',
                'phone': metadata.get('phone', '') if metadata else '',
            },
            'return_params': json.dumps({
                'user_id': user_id,
                'plan_id': plan_id,
                **(metadata or {})
            }),
            'return_url': self.return_url or success_url,  # Webhook/callback URL
            'redirect_url': success_url,  # Post-payment redirect
            'cancel_url': cancel_url,
        }
        
        # Call PayWay Create Transaction API
        response = self._make_request('POST', '/v1/transactions/create', transaction_data)
        
        # PayWay returns HTML that contains the checkout interface
        checkout_html = response.get('html_response', '')
        
        return {
            'session_id': response.get('tran_id'),
            'transaction_id': response.get('tran_id'),
            'checkout_html': checkout_html,  # Render this HTML on your website
            'provider': self.provider_name,
            'amount': amount,
            'currency': currency,
            'metadata': {
                'user_id': user_id,
                'plan_id': plan_id,
                **(metadata or {})
            }
        }
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create recurring subscription.
        
        Note: PayWay handles recurring payments via Credentials on File (CoF) APIs
        which require explicit customer authorization and card tokenization.
        """
        data = {
            'merchant_id': self.merchant_id,
            'customer_id': customer_id,
            'plan_id': price_id,
            'trial_days': trial_days,
            'metadata': metadata or {}
        }
        
        response = self._make_request('POST', '/v1/subscriptions/create', data)
        
        return {
            'subscription_id': response.get('subscription_id'),
            'status': response.get('status'),
            'current_period_start': datetime.fromisoformat(response['current_period_start']),
            'current_period_end': datetime.fromisoformat(response['current_period_end']),
        }
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Cancel a PayWay subscription."""
        data = {
            'subscription_id': subscription_id,
            'cancel_immediately': immediate,
        }
        
        response = self._make_request('POST', '/v1/subscriptions/cancel', data)
        
        return {
            'subscription_id': subscription_id,
            'status': response.get('status'),
            'cancelled_at': datetime.now(tz=timezone.utc),
        }
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify PayWay webhook signature.
        
        PayWay sends callback with signature in header for verification.
        """
        try:
            # Verify signature
            expected_signature = self._generate_signature(payload.decode('utf-8'))
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def process_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process PayWay webhook events.
        
        PayWay sends payment status updates via callback/return_url with:
        - tran_id: Transaction ID
        - apv: Approval code
        - status: Payment status (0=success, other=failure)
        - return_params: Custom metadata sent during transaction creation
        """
        logger.info(f"Processing PayWay webhook: {event_type}")
        
        processed_data = {
            'provider': self.provider_name,
            'event_type': event_type,
        }
        
        # Parse return_params to extract metadata
        return_params = {}
        if 'return_params' in event_data:
            try:
                return_params = json.loads(event_data['return_params'])
            except json.JSONDecodeError:
                pass
        
        if event_type == 'payment.completed' or event_data.get('status') == '0':
            processed_data.update({
                'status': 'succeeded',
                'transaction_id': event_data.get('tran_id'),
                'approval_code': event_data.get('apv'),
                'metadata': return_params,
            })
        elif event_data.get('status') != '0':
            processed_data.update({
                'status': 'failed',
                'transaction_id': event_data.get('tran_id'),
                'error': event_data.get('error_message', 'Payment failed'),
                'metadata': return_params,
            })
        
        return processed_data
    
    def get_payment_status(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """Get PayWay payment/transaction status."""
        data = {
            'tran_id': payment_id,
        }
        
        response = self._make_request('POST', '/v1/transactions/check', data)
        
        status_map = {
            '0': 'succeeded',
            '1': 'pending',
            '2': 'failed',
            '3': 'cancelled',
        }
        
        return {
            'payment_id': payment_id,
            'status': status_map.get(response.get('status'), 'unknown'),
            'amount': Decimal(response.get('amount', 0)) / (100 if response.get('currency') == 'USD' else 1),
            'currency': response.get('currency', ''),
            'approval_code': response.get('apv'),
        }
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Refund a PayWay payment."""
        data = {
            'tran_id': payment_id,
        }
        
        if amount:
            # Convert to minor units
            data['refund_amount'] = int(amount * 100)
        
        response = self._make_request('POST', '/v1/transactions/refund', data)
        
        return {
            'refund_id': response.get('refund_id'),
            'status': response.get('status'),
            'amount': amount or Decimal(response.get('amount', 0)) / 100,
        }
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a customer/account in PayWay.
        
        For recurring payments, customer account is needed for card tokenization.
        """
        data = {
            'email': email,
            'name': name,
            'metadata': metadata or {}
        }
        
        response = self._make_request('POST', '/v1/customers/create', data)
        
        return {
            'customer_id': response.get('customer_id'),
            'email': email,
        }
    
    def supports_subscriptions(self) -> bool:
        """PayWay supports subscriptions via Credentials on File."""
        return True
    
    def supports_refunds(self) -> bool:
        """PayWay supports refunds."""
        return True
    
    def get_supported_currencies(self) -> list:
        """PayWay supports USD and KHR."""
        return ['USD', 'KHR']
