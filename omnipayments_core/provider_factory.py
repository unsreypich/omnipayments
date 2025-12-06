"""
Payment Provider Factory
Manages provider instances and configuration
"""
from typing import Dict, Any, Optional
from .providers import BasePaymentProvider, StripeProvider, BakongProvider, PayWayProvider
import logging

logger = logging.getLogger(__name__)


class PaymentProviderFactory:
    """
    Factory for creating and managing payment provider instances.
    
    Usage:
        provider = PaymentProviderFactory.get_provider('stripe', config)
        session = provider.create_checkout_session(...)
    """
    
    # Registry of available providers
    _providers = {
        'stripe': StripeProvider,
        'bakong': BakongProvider,
        'payway': PayWayProvider,
    }
    
    # Cache of instantiated providers
    _instances: Dict[str, BasePaymentProvider] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a new payment provider.
        
        Args:
            name: Provider identifier (e.g., 'stripe', 'bakong')
            provider_class: Provider class implementing BasePaymentProvider
        """
        if not issubclass(provider_class, BasePaymentProvider):
            raise ValueError(
                f"Provider {provider_class} must inherit from BasePaymentProvider"
            )
        
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered payment provider: {name}")
    
    @classmethod
    def get_provider(
        cls,
        provider_name: str,
        config: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> BasePaymentProvider:
        """
        Get a payment provider instance.
        
        Args:
            provider_name: Name of the provider ('stripe', 'bakong', etc.)
            config: Provider configuration dictionary
            use_cache: Whether to use cached instance (default: True)
        
        Returns:
            Configured provider instance
        
        Raises:
            ValueError: If provider not found or config invalid
        """
        provider_name = provider_name.lower()
        
        # Check if provider exists
        if provider_name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown payment provider '{provider_name}'. "
                f"Available providers: {available}"
            )
        
        # Return cached instance if available and caching enabled
        cache_key = f"{provider_name}_{id(config)}"
        if use_cache and cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Create new instance
        provider_class = cls._providers[provider_name]
        
        try:
            provider = provider_class(config or {})
            
            # Cache the instance
            if use_cache:
                cls._instances[cache_key] = provider
            
            logger.info(f"Initialized payment provider: {provider_name}")
            return provider
        
        except Exception as e:
            logger.error(f"Failed to initialize provider '{provider_name}': {str(e)}")
            raise
    
    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of registered provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached provider instances."""
        cls._instances.clear()
        logger.info("Cleared provider cache")
    
    @classmethod
    def get_provider_info(cls, provider_name: str) -> Dict[str, Any]:
        """
        Get information about a provider.
        
        Args:
            provider_name: Name of the provider
        
        Returns:
            Dictionary with provider capabilities and info
        """
        provider_name = provider_name.lower()
        
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        
        # Create temporary instance with empty config to check capabilities
        try:
            temp_provider = provider_class({})
        except:
            # If provider requires config, use dummy values
            temp_provider = None
        
        info = {
            'name': provider_name,
            'class': provider_class.__name__,
            'module': provider_class.__module__,
        }
        
        if temp_provider:
            info.update({
                'supports_subscriptions': temp_provider.supports_subscriptions(),
                'supports_refunds': temp_provider.supports_refunds(),
                'supported_currencies': temp_provider.get_supported_currencies(),
            })
        
        return info


# Convenience function for quick provider access
def get_provider(provider_name: str, config: Dict[str, Any]) -> BasePaymentProvider:
    """
    Convenience function to get a payment provider.
    
    Example:
        from payment_subscriptions.provider_factory import get_provider
        
        stripe = get_provider('stripe', {
            'secret_key': 'sk_test_...',
            'publishable_key': 'pk_test_...'
        })
        
        session = stripe.create_checkout_session(...)
    """
    return PaymentProviderFactory.get_provider(provider_name, config)
