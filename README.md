# OmniPayments

**Framework-agnostic payment provider system for Python**

Works with **Django**, **Flask**, **FastAPI**, and any Python framework!

## 🚀 Features

- ✅ **Framework Agnostic** - Works with Django, Flask, FastAPI, plain Python
- ✅ **Multi-Provider** - Stripe, Bakong KHQR, easily add more
- ✅ **Unified Interface** - Same code for all payment providers
- ✅ **Production Ready** - Webhooks, signatures, error handling
- ✅ **Type Safe** - Full type hints throughout
- ✅ **Zero Dependencies** - Core has no framework requirements

## 📦 Installation

```bash
pip install omnipayments
```

## 🎯 Quick Start

### With Any Framework

```python
from omnipayments import get_provider

# Configure provider
stripe = get_provider('stripe', {
    'secret_key': 'sk_test_...',
    'publishable_key': 'pk_test_...',
})

# Create payment
session = stripe.create_checkout_session(
    amount=Decimal('29.99'),
    currency='USD',
    user_id='user_123',
    plan_id='plan_456',
    success_url='https://example.com/success',
    cancel_url='https://example.com/cancel',
)

print(session['session_url'])  # Redirect user here
```

### With Django

```python
from omnipayments import get_provider
from django.conf import settings
from django.shortcuts import redirect

def checkout(request, plan_id):
    provider = get_provider('stripe', settings.STRIPE_CONFIG)
    
    session = provider.create_checkout_session(
        amount=plan.price,
        currency='USD',
        user_id=str(request.user.id),
        plan_id=str(plan_id),
        success_url=request.build_absolute_uri('/success'),
        cancel_url=request.build_absolute_uri('/cancel'),
    )
    
    return redirect(session['session_url'])
```

### With Flask

```python
from omnipayments import get_provider
from flask import Flask, redirect, request

app = Flask(__name__)

@app.route('/checkout/<plan_id>')
def checkout(plan_id):
    provider = get_provider('stripe', app.config['STRIPE_CONFIG'])
    
    session = provider.create_checkout_session(
        amount=29.99,
        currency='USD',
        user_id=request.user.id,
        plan_id=plan_id,
        success_url=url_for('success', _external=True),
        cancel_url=url_for('cancel', _external=True),
    )
    
    return redirect(session['session_url'])
```

### With FastAPI

```python
from omnipayments import get_provider
from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.post("/checkout/{plan_id}")
async def checkout(plan_id: str, user = Depends(get_current_user)):
    provider = get_provider('stripe', app.state.stripe_config)
    
    session = provider.create_checkout_session(
        amount=29.99,
        currency='USD',
        user_id=user.id,
        plan_id=plan_id,
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    
    return RedirectResponse(session['session_url'])
```

## 🎨 Supported Providers

### Stripe
```python
provider = get_provider('stripe', {
    'secret_key': 'sk_test_...',
    'publishable_key': 'pk_test_...',
    'webhook_secret': 'whsec_...',
})
```

### Bakong KHQR (Cambodia)
```python
provider = get_provider('bakong', {
    'merchant_id': 'your_merchant_id',
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret',
    'use_sandbox': True,
})

# Returns QR code for user to scan
payment = provider.create_checkout_session(
    amount=119600,  # KHR
    currency='KHR',
    user_id='user_123',
    plan_id='plan_456',
    success_url='...',
    cancel_url='...',
)

qr_code = payment['qr_code']  # base64 PNG image
```

## 🔧 Provider Interface

All providers implement the same interface:

```python
class BasePaymentProvider:
    def create_checkout_session(...) -> Dict
    def create_subscription(...) -> Dict
    def cancel_subscription(...) -> Dict
    def verify_webhook(...) -> bool
    def process_webhook(...) -> Dict
    def get_payment_status(...) -> Dict
    def refund_payment(...) -> Dict
    def create_customer(...) -> Dict
    def supports_subscriptions() -> bool
    def supports_refunds() -> bool
    def get_supported_currencies() -> list
```

## 🌟 Why OmniPayments?

1. **Framework Independent** - Use the same payment code across all your Python projects
2. **Provider Agnostic** - Switch providers without changing your code
3. **Type Safe** - Full type hints for better IDE support
4. **Production Ready** - Battle-tested patterns from spree_vpago
5. **Easy to Extend** - Add custom providers easily

## 🔌 Adding Custom Providers

```python
from omnipayments import BasePaymentProvider, PaymentProviderFactory

class MyProvider(BasePaymentProvider):
    provider_name = "myprovider"
    
    def validate_config(self):
        # Validate config
        pass
    
    def create_checkout_session(self, ...):
        # Implement payment logic
        pass
    
    # Implement other required methods...

# Register your provider
PaymentProviderFactory.register_provider('myprovider', MyProvider)

# Use it
provider = get_provider('myprovider', config)
```


## 🧪 Testing

```bash
pip install omnipayments[dev]
pytest
```

## 📖 Documentation

Full documentation: https://omnipayments.readthedocs.io

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md

## 📄 License

MIT License - see LICENSE file

---

**Built with ❤️ for the Python community**

*Supporting all frameworks, all payment providers*
