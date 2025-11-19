"""
OmniPayments - Framework-Agnostic Payment Provider System
Works with Django, Flask, FastAPI, and any Python framework
"""

__version__ = "1.0.0"

from .provider_factory import PaymentProviderFactory, get_provider
from .providers import BasePaymentProvider, StripeProvider, BakongProvider

__all__ = [
    'PaymentProviderFactory',
    'get_provider',
    'BasePaymentProvider',
    'StripeProvider',
    'BakongProvider',
]
