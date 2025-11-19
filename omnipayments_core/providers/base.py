"""
Base Payment Provider Interface
All payment providers must implement this interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal


class BasePaymentProvider(ABC):
    """
    Abstract base class for payment providers.
    Similar to payment gateway adapters in spree_vpago.
    """
    
    provider_name: str = "base"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize payment provider with configuration.
        
        Args:
            config: Provider-specific configuration (API keys, URLs, etc.)
        """
        self.config = config
        self.validate_config()
    
    @abstractmethod
    def validate_config(self):
        """Validate that required configuration is present."""
        pass
    
    @abstractmethod
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
        Create a checkout/payment session.
        
        Returns:
            {
                'session_id': str,
                'session_url': str,  # URL to redirect user to
                'provider': str,
                'metadata': dict
            }
        """
        pass
    
    @abstractmethod
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a recurring subscription.
        
        Returns:
            {
                'subscription_id': str,
                'status': str,
                'current_period_start': datetime,
                'current_period_end': datetime,
            }
        """
        pass
    
    @abstractmethod
    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Provider's subscription ID
            immediate: Cancel immediately or at period end
        
        Returns:
            {
                'subscription_id': str,
                'status': str,
                'cancelled_at': datetime,
            }
        """
        pass
    
    @abstractmethod
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature for security.
        
        Returns:
            True if signature is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def process_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process webhook event from payment provider.
        
        Returns:
            {
                'status': str,
                'event_type': str,
                'processed_data': dict
            }
        """
        pass
    
    @abstractmethod
    def get_payment_status(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """
        Get status of a payment transaction.
        
        Returns:
            {
                'payment_id': str,
                'status': str,  # 'pending', 'succeeded', 'failed'
                'amount': Decimal,
                'currency': str,
            }
        """
        pass
    
    @abstractmethod
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment (full or partial).
        
        Returns:
            {
                'refund_id': str,
                'status': str,
                'amount': Decimal,
            }
        """
        pass
    
    @abstractmethod
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a customer in the payment provider.
        
        Returns:
            {
                'customer_id': str,
                'email': str,
            }
        """
        pass
    
    def supports_subscriptions(self) -> bool:
        """Check if provider supports recurring subscriptions."""
        return True
    
    def supports_refunds(self) -> bool:
        """Check if provider supports refunds."""
        return True
    
    def get_supported_currencies(self) -> list:
        """Get list of supported currencies."""
        return ['USD']
