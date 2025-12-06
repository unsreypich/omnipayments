# PayWay Quick Reference

## Installation

```bash
# Already integrated into OmniPayments
# Just configure environment variables
```

## Configuration

```dotenv
# .env file
PAYWAY_MERCHANT_ID=your_merchant_id
PAYWAY_API_KEY=your_api_key
PAYWAY_API_SECRET=your_api_secret
PAYWAY_SANDBOX=True  # False for production
PAYWAY_RETURN_URL=https://api.your-domain.com/api/payments/payway/callback/
PAYWAY_CURRENCY=USD  # or KHR
```

## Basic Usage

```python
from omnipayments import get_provider
from django.conf import settings
from decimal import Decimal

# Initialize provider
payway = get_provider('payway', {
    'merchant_id': settings.PAYWAY_MERCHANT_ID,
    'api_key': settings.PAYWAY_API_KEY,
    'api_secret': settings.PAYWAY_API_SECRET,
    'sandbox': settings.PAYWAY_SANDBOX,
    'return_url': settings.PAYWAY_RETURN_URL,
})
```

## Common Operations

### 1. Create Payment Checkout
```python
session = payway.create_checkout_session(
    amount=Decimal('29.99'),
    currency='USD',
    user_id='user_123',
    plan_id='plan_456',
    success_url='https://example.com/success',
    cancel_url='https://example.com/cancel',
    metadata={
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
    }
)

# Render in frontend
html = session['checkout_html']
transaction_id = session['transaction_id']
```

### 2. Check Payment Status
```python
status = payway.get_payment_status('tran_123456')
print(status['status'])  # 'succeeded', 'failed', 'pending', 'cancelled'
```

### 3. Refund Payment
```python
# Full refund
refund = payway.refund_payment('tran_123456')

# Partial refund
refund = payway.refund_payment('tran_123456', Decimal('10.00'))

print(refund['status'])  # 'succeeded'
```

### 4. Handle Webhook Callback
```python
import json
from django.http import JsonResponse

def payway_callback(request):
    payload = request.body
    signature = request.headers.get('X-PayWay-Signature', '')
    data = json.loads(payload)
    
    # Verify signature
    if not payway.verify_webhook(payload, signature, settings.PAYWAY_API_SECRET):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Process webhook
    result = payway.process_webhook('payment.completed', data)
    
    # Update database
    if result['status'] == 'succeeded':
        # Payment successful
        pass
    elif result['status'] == 'failed':
        # Payment failed
        pass
    
    return JsonResponse({'status': 'processed'})
```

### 5. Create Subscription (Recurring Payment)
```python
subscription = payway.create_subscription(
    customer_id='customer_123',
    price_id='price_456',
    trial_days=14,
)

print(subscription['subscription_id'])
print(subscription['status'])
```

### 6. Cancel Subscription
```python
cancelled = payway.cancel_subscription(
    subscription_id='sub_789',
    immediate=False  # or True for immediate cancellation
)
```

## Response Format

### Checkout Session
```python
{
    'session_id': 'tran_user_123_plan_456_1234567890',
    'transaction_id': 'tran_user_123_plan_456_1234567890',
    'checkout_html': '<html>...</html>',  # HTML to render
    'provider': 'payway',
    'amount': Decimal('29.99'),
    'currency': 'USD',
    'metadata': {...}
}
```

### Payment Status
```python
{
    'payment_id': 'tran_123456',
    'status': 'succeeded',           # 'succeeded' | 'failed' | 'pending' | 'cancelled'
    'amount': Decimal('29.99'),
    'currency': 'USD',
    'approval_code': '123456'
}
```

### Webhook Callback (from PayWay)
```python
{
    "tran_id": "transaction_id",
    "apv": "approval_code",
    "status": "0",                   # "0" = success, "1" = pending, "2" = failed, "3" = cancelled
    "return_params": "{...}"         # Your metadata
}
```

## Test Cards (Sandbox)

```
Success:
  Card: 4000 0000 0000 0002
  Expiry: Any future date (MM/YY)
  CVV: Any 3 digits

Failure:
  Card: 4000 0000 0000 0009
  Expiry: Any future date (MM/YY)
  CVV: Any 3 digits
```

## Supported Currencies

- **USD** - US Dollar (convert to cents)
- **KHR** - Cambodian Riel (integer amounts)

```python
# USD example
payway.create_checkout_session(amount=Decimal('29.99'), currency='USD')

# KHR example
payway.create_checkout_session(amount=Decimal('119600'), currency='KHR')
```

## Payment Methods

- 💳 Credit/Debit Cards
- 📱 ABA Pay
- 📲 KHQR (QR Code)
- 🌐 WeChat Pay
- 🌐 Alipay
- 🛒 Google Pay

All available in checkout - customer chooses their preferred method.

## Supported Operations

| Operation | Method | Status |
|-----------|--------|--------|
| Create checkout | `create_checkout_session()` | ✅ |
| Get payment status | `get_payment_status()` | ✅ |
| Refund payment | `refund_payment()` | ✅ |
| Create subscription | `create_subscription()` | ✅ |
| Cancel subscription | `cancel_subscription()` | ✅ |
| Create customer | `create_customer()` | ✅ |
| Verify webhook | `verify_webhook()` | ✅ |
| Process webhook | `process_webhook()` | ✅ |

## Common Errors

| Error | Solution |
|-------|----------|
| Invalid webhook signature | Verify `PAYWAY_API_SECRET` and check URL is whitelisted |
| Merchant not found | Verify `PAYWAY_MERCHANT_ID` and credentials |
| Currency not supported | Use USD or KHR only |
| API timeout | Retry with exponential backoff |

## Integration Checklist

- [ ] Set up sandbox account at https://sandbox.payway.com.kh/
- [ ] Get API credentials (Merchant ID, API Key, Secret)
- [ ] Add environment variables to `.env`
- [ ] Add return URL to PayWay merchant profile whitelist
- [ ] Test checkout session creation
- [ ] Test payment with test card
- [ ] Verify webhook callback is received
- [ ] Update payment status in database
- [ ] Create subscription for user
- [ ] Test refund functionality
- [ ] Deploy to production
- [ ] Update production credentials
- [ ] Verify production webhook URL

## Useful Links

- **PayWay Developer Docs**: https://developer.payway.com.kh/
- **Sandbox Registration**: https://sandbox.payway.com.kh/register-sandbox/
- **Sandbox Dashboard**: https://sandbox.payway.com.kh/dashboard/
- **Production Dashboard**: https://dashboard.payway.com.kh/
- **PayWay Support**: contact@payway.com.kh

## Code Examples

### Django REST Framework Endpoint
```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payway_checkout(request):
    plan_id = request.data.get('plan_id')
    
    session = payway.create_checkout_session(
        amount=plan.price,
        currency='USD',
        user_id=str(request.user.id),
        plan_id=str(plan_id),
        success_url=request.build_absolute_uri('/success'),
        cancel_url=request.build_absolute_uri('/cancel'),
    )
    
    return Response(session)
```

### React Component
```jsx
function PayWayCheckout({ planId }) {
  const handleCheckout = async () => {
    const response = await fetch('/api/payway/checkout/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ plan_id: planId })
    });
    
    const data = await response.json();
    document.body.innerHTML += data.checkout_html;
  };
  
  return <button onClick={handleCheckout}>Pay with PayWay</button>;
}
```

### Webhook Handler
```python
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json

@require_http_methods(["POST"])
def payway_webhook(request):
    payload = request.body
    data = json.loads(payload)
    signature = request.headers.get('X-PayWay-Signature', '')
    
    # Verify and process
    if payway.verify_webhook(payload, signature, settings.PAYWAY_API_SECRET):
        result = payway.process_webhook('payment.completed', data)
        # Update database...
        return JsonResponse({'status': 'processed'})
    
    return JsonResponse({'error': 'Invalid signature'}, status=400)
```

## Performance Tips

1. **Cache provider instances** - Don't create new provider for every request
2. **Implement webhook queue** - Process webhooks asynchronously with Celery
3. **Add retry logic** - Exponential backoff for API failures
4. **Rate limiting** - Implement on webhook endpoint to prevent abuse
5. **Logging** - Log all payment transactions for debugging

## Security Notes

- 🔒 Never commit API credentials to code
- 🔒 Use environment variables or secrets manager
- 🔒 Always verify webhook signatures
- 🔒 Use HTTPS for all URLs
- 🔒 Whitelist webhook URL in PayWay dashboard
- 🔒 Implement proper error handling (don't expose secrets in errors)

---

**Last Updated**: 2025

For detailed documentation, see:
- `/server/docs/payment/payway/README.md`
- `/server/docs/payment/payway/INTEGRATION_GUIDE.md`
