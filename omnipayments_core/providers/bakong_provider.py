"""
Bakong KHQR Payment Provider
Cambodia's national payment system - QR code based payments
"""
import requests
import hmac
import hashlib
import json
import base64
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from .base import BasePaymentProvider
import logging

logger = logging.getLogger(__name__)


class BakongProvider(BasePaymentProvider):
    """
    Bakong KHQR payment provider implementation.
    
    Bakong is Cambodia's national payment system operated by NBC (National Bank of Cambodia).
    Supports QR code payments (KHQR - Khmer QR).
    
    Configuration required:
    - BAKONG_MERCHANT_ID: Your merchant ID
    - BAKONG_API_KEY: API key for authentication
    - BAKONG_API_SECRET: API secret for signing requests
    - BAKONG_API_URL: API endpoint (production/sandbox)
    """
    
    provider_name = "bakong"
    
    # Bakong API endpoints
    PRODUCTION_URL = "https://api-bakong.nbc.gov.kh"
    SANDBOX_URL = "https://api-sandbox-bakong.nbc.gov.kh"
    
    def __init__(self, config: Dict[str, Any]):
        self.merchant_id = None
        self.api_key = None
        self.api_secret = None
        self.api_url = None
        self.is_sandbox = None
        super().__init__(config)
    
    def validate_config(self):
        """Validate Bakong configuration."""
        required_fields = ['merchant_id', 'api_key', 'api_secret']
        
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Bakong provider requires '{field}' in configuration")
        
        self.merchant_id = self.config['merchant_id']
        self.api_key = self.config['api_key']
        self.api_secret = self.config['api_secret']
        self.is_sandbox = self.config.get('sandbox', True)
        self.api_url = self.SANDBOX_URL if self.is_sandbox else self.PRODUCTION_URL
    
    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for API requests."""
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
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
        """Make authenticated API request to Bakong."""
        url = f"{self.api_url}{endpoint}"
        
        # Prepare payload
        payload = json.dumps(data) if data else ""
        timestamp = str(int(datetime.now().timestamp()))
        
        # Generate signature: timestamp + method + endpoint + payload
        sign_string = f"{timestamp}{method}{endpoint}{payload}"
        signature = self._generate_signature(sign_string)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Bakong-Merchant-ID': self.merchant_id,
            'X-Bakong-API-Key': self.api_key,
            'X-Bakong-Timestamp': timestamp,
            'X-Bakong-Signature': signature,
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
            logger.error(f"Bakong API request failed: {str(e)}")
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
        Create a KHQR payment session.
        
        Returns QR code data for user to scan with banking app.
        """
        if currency.upper() not in ['KHR', 'USD']:
            raise ValueError("Bakong only supports KHR and USD currencies")
        
        # Convert amount to smallest unit (cents for USD, riel for KHR)
        amount_minor = int(amount * 100) if currency.upper() == 'USD' else int(amount)
        
        # Create payment request
        data = {
            'merchantId': self.merchant_id,
            'amount': amount_minor,
            'currency': currency.upper(),
            'orderId': f"order_{user_id}_{plan_id}_{int(datetime.now().timestamp())}",
            'description': f"Subscription to plan {plan_id}",
            'callbackUrl': success_url,  # Webhook URL for payment confirmation
            'returnUrl': success_url,
            'cancelUrl': cancel_url,
            'metadata': {
                'user_id': user_id,
                'plan_id': plan_id,
                **(metadata or {})
            }
        }
        
        response = self._make_request('POST', '/v1/payments/qr/create', data)
        
        # Bakong returns QR code data
        return {
            'session_id': response['transactionId'],
            'session_url': response.get('paymentUrl'),  # URL to payment page
            'qr_code': response['qrCode'],  # Base64 encoded QR image
            'qr_string': response['qrString'],  # KHQR string for direct scanning
            'provider': self.provider_name,
            'amount': amount,
            'currency': currency,
            'expires_at': response.get('expiresAt'),
            'metadata': data['metadata']
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
        
        Note: Bakong subscriptions require customer approval for recurring payments.
        """
        data = {
            'merchantId': self.merchant_id,
            'customerId': customer_id,
            'planId': price_id,
            'trialDays': trial_days,
            'metadata': metadata or {}
        }
        
        response = self._make_request('POST', '/v1/subscriptions/create', data)
        
        return {
            'subscription_id': response['subscriptionId'],
            'status': response['status'],  # 'pending_approval', 'active', etc.
            'current_period_start': datetime.fromisoformat(response['currentPeriodStart']),
            'current_period_end': datetime.fromisoformat(response['currentPeriodEnd']),
            'approval_url': response.get('approvalUrl'),  # URL for customer to approve
        }
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """Cancel a Bakong subscription."""
        data = {
            'subscriptionId': subscription_id,
            'immediate': immediate
        }
        
        response = self._make_request('POST', '/v1/subscriptions/cancel', data)
        
        return {
            'subscription_id': subscription_id,
            'status': response['status'],
            'cancelled_at': datetime.fromisoformat(response['cancelledAt']),
        }
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify Bakong webhook signature."""
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def process_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Bakong webhook events.
        
        Event types:
        - payment.completed
        - payment.failed
        - subscription.activated
        - subscription.cancelled
        - subscription.payment_succeeded
        - subscription.payment_failed
        """
        logger.info(f"Processing Bakong webhook: {event_type}")
        
        processed_data = {
            'provider': self.provider_name,
            'event_type': event_type,
            'transaction_id': event_data.get('transactionId'),
            'status': event_data.get('status'),
        }
        
        # Map Bakong events to standard payment events
        if event_type == 'payment.completed':
            processed_data.update({
                'payment_status': 'succeeded',
                'amount': Decimal(event_data['amount']) / 100,
                'currency': event_data['currency'],
                'customer_id': event_data.get('customerId'),
                'metadata': event_data.get('metadata', {}),
            })
        
        elif event_type == 'payment.failed':
            processed_data.update({
                'payment_status': 'failed',
                'error_code': event_data.get('errorCode'),
                'error_message': event_data.get('errorMessage'),
            })
        
        elif event_type == 'subscription.payment_succeeded':
            processed_data.update({
                'subscription_id': event_data['subscriptionId'],
                'payment_status': 'succeeded',
                'amount': Decimal(event_data['amount']) / 100,
                'currency': event_data['currency'],
                'billing_reason': 'subscription_cycle',
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
        """Get Bakong payment status."""
        response = self._make_request('GET', f'/v1/payments/{payment_id}')
        
        # Map Bakong status to standard status
        status_map = {
            'pending': 'pending',
            'completed': 'succeeded',
            'failed': 'failed',
            'expired': 'failed',
        }
        
        return {
            'payment_id': payment_id,
            'status': status_map.get(response['status'], 'pending'),
            'amount': Decimal(response['amount']) / 100,
            'currency': response['currency'],
            'paid_at': datetime.fromisoformat(response['paidAt']) if response.get('paidAt') else None,
        }
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Refund a Bakong payment.
        
        Note: Bakong refunds may take 1-3 business days to process.
        """
        data = {
            'transactionId': payment_id,
        }
        
        if amount:
            data['amount'] = int(amount * 100)  # Convert to minor units
        
        response = self._make_request('POST', '/v1/payments/refund', data)
        
        return {
            'refund_id': response['refundId'],
            'status': response['status'],  # 'pending', 'completed'
            'amount': Decimal(response['amount']) / 100,
            'estimated_arrival': response.get('estimatedArrival'),
        }
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a customer in Bakong system."""
        data = {
            'email': email,
            'name': name,
            'metadata': metadata or {}
        }
        
        response = self._make_request('POST', '/v1/customers/create', data)
        
        return {
            'customer_id': response['customerId'],
            'email': email,
            'name': name,
        }
    
    def supports_subscriptions(self) -> bool:
        """Bakong supports recurring subscriptions."""
        return True
    
    def supports_refunds(self) -> bool:
        """Bakong supports refunds."""
        return True
    
    def get_supported_currencies(self) -> list:
        """Bakong supports KHR (Cambodian Riel) and USD."""
        return ['KHR', 'USD']
    
    def generate_khqr_string(
        self,
        amount: Decimal,
        currency: str,
        merchant_name: str,
        bill_number: str
    ) -> str:
        """
        Generate KHQR string manually (EMVCo format).
        
        This is useful for generating QR codes without API calls.
        """
        # KHQR follows EMVCo QR Code Specification
        # Format: Tag-Length-Value (TLV)
        
        currency_code = '116' if currency.upper() == 'KHR' else '840'  # USD
        amount_str = f"{amount:.2f}"
        
        # Build KHQR string (simplified)
        khqr_parts = [
            '00020101',  # Payload Format Indicator
            '01021',     # Point of Initiation Method (static)
            f'30{len(self.merchant_id):02d}{self.merchant_id}',  # Merchant Account
            '5204',      # Merchant Category Code
            f'5303{currency_code}',  # Transaction Currency
            f'54{len(amount_str):02d}{amount_str}',  # Transaction Amount
            '5802KH',    # Country Code (Cambodia)
            f'59{len(merchant_name):02d}{merchant_name}',  # Merchant Name
            f'62{len(bill_number) + 4:02d}05{len(bill_number):02d}{bill_number}',  # Bill Number
        ]
        
        khqr_string = ''.join(khqr_parts)
        
        # Add CRC checksum (last 4 digits)
        crc = self._calculate_crc(khqr_string + '6304')
        khqr_string += f'6304{crc}'
        
        return khqr_string
    
    def _calculate_crc(self, data: str) -> str:
        """Calculate CRC-16/CCITT-FALSE checksum for KHQR."""
        crc = 0xFFFF
        for char in data:
            crc ^= ord(char) << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return f"{crc:04X}"
