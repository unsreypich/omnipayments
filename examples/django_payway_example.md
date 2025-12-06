# Django REST API Example - PayWay Integration

This example shows how to integrate PayWay with Django REST Framework.

## Setup

### 1. Create Django App

```bash
python manage.py startapp payments
```

### 2. Create Models

```python
# payments/models.py
from django.db import models
from django.contrib.auth.models import User

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_provider = models.CharField(
        max_length=20,
        choices=[('stripe', 'Stripe'), ('bakong', 'Bakong'), ('payway', 'PayWay')],
        default='payway'
    )

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    payment_provider = models.CharField(max_length=20)
    provider_customer_id = models.CharField(max_length=255)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    provider_transaction_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PaymentTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)
    transaction_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20)
    payment_provider = models.CharField(max_length=20)
    response_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3. Create Serializers

```python
# payments/serializers.py
from rest_framework import serializers
from .models import SubscriptionPlan, Subscription, PaymentTransaction

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'price', 'currency', 'payment_provider']

class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer()
    
    class Meta:
        model = Subscription
        fields = ['id', 'user', 'plan', 'payment_provider', 'status', 'created_at']

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = ['id', 'user', 'transaction_id', 'amount', 'currency', 'status', 'created_at']
```

### 4. Create ViewSet

```python
# payments/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from omnipayments import get_provider
from decimal import Decimal
import json

from .models import SubscriptionPlan, Subscription, PaymentTransaction
from .serializers import SubscriptionPlanSerializer, SubscriptionSerializer
from app.base.services.payment.payment_service import MultiProviderPaymentService

class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def payway_checkout(self, request):
        """
        Create PayWay checkout session
        
        POST /api/subscriptions/payway_checkout/
        {
            "plan_id": 1
        }
        """
        try:
            plan_id = request.data.get('plan_id')
            plan = SubscriptionPlan.objects.get(id=plan_id, payment_provider='payway')
            
            # Get PayWay provider
            payway = get_provider('payway', {
                'merchant_id': settings.PAYWAY_MERCHANT_ID,
                'api_key': settings.PAYWAY_API_KEY,
                'api_secret': settings.PAYWAY_API_SECRET,
                'sandbox': settings.PAYWAY_SANDBOX,
                'return_url': settings.PAYWAY_RETURN_URL,
            })
            
            # Create checkout session
            session = payway.create_checkout_session(
                amount=plan.price,
                currency=plan.currency,
                user_id=str(request.user.id),
                plan_id=str(plan.id),
                success_url=request.build_absolute_uri('/subscription/success'),
                cancel_url=request.build_absolute_uri('/subscription/cancel'),
                metadata={
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                }
            )
            
            return Response({
                'transaction_id': session['transaction_id'],
                'checkout_html': session['checkout_html'],
            }, status=status.HTTP_201_CREATED)
        
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def payway_callback(self, request):
        """
        Handle PayWay payment callback (webhook)
        
        Called by PayWay when payment is completed
        """
        try:
            payload = request.body
            signature = request.headers.get('X-PayWay-Signature', '')
            
            # Process webhook using service
            result = MultiProviderPaymentService.handle_webhook(
                provider_name='payway',
                payload=payload,
                signature=signature,
                event_type='payment.completed',
                event_data=request.data
            )
            
            return Response({'status': 'processed'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def payment_status(self, request):
        """
        Check payment status
        
        GET /api/subscriptions/payment_status/?transaction_id=tran_123456
        """
        try:
            transaction_id = request.query_params.get('transaction_id')
            if not transaction_id:
                return Response(
                    {'error': 'transaction_id required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get PayWay provider
            payway = get_provider('payway', {
                'merchant_id': settings.PAYWAY_MERCHANT_ID,
                'api_key': settings.PAYWAY_API_KEY,
                'api_secret': settings.PAYWAY_API_SECRET,
                'sandbox': settings.PAYWAY_SANDBOX,
                'return_url': settings.PAYWAY_RETURN_URL,
            })
            
            # Get status
            status_info = payway.get_payment_status(transaction_id)
            
            return Response(status_info, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def refund_payment(self, request):
        """
        Refund a payment
        
        POST /api/subscriptions/refund_payment/
        {
            "transaction_id": "tran_123456",
            "amount": 10.00  // Optional - full refund if omitted
        }
        """
        try:
            transaction_id = request.data.get('transaction_id')
            amount = request.data.get('amount')
            
            if not transaction_id:
                return Response(
                    {'error': 'transaction_id required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get PayWay provider
            payway = get_provider('payway', {
                'merchant_id': settings.PAYWAY_MERCHANT_ID,
                'api_key': settings.PAYWAY_API_KEY,
                'api_secret': settings.PAYWAY_API_SECRET,
                'sandbox': settings.PAYWAY_SANDBOX,
                'return_url': settings.PAYWAY_RETURN_URL,
            })
            
            # Refund
            refund = payway.refund_payment(
                payment_id=transaction_id,
                amount=Decimal(amount) if amount else None
            )
            
            return Response(refund, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    
    @action(detail=False, methods=['get'])
    def payway_plans(self, request):
        """Get PayWay subscription plans"""
        plans = SubscriptionPlan.objects.filter(payment_provider='payway')
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)
```

### 5. Configure URLs

```python
# payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet, SubscriptionPlanViewSet

router = DefaultRouter()
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'plans', SubscriptionPlanViewSet, basename='plan')

urlpatterns = [
    path('', include(router.urls)),
]

# In your main urls.py:
# path('api/payments/', include('payments.urls')),
```

## API Usage Examples

### 1. Get Available Plans

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/payments/plans/payway_plans/
```

Response:
```json
[
    {
        "id": 1,
        "name": "Premium",
        "price": "29.99",
        "currency": "USD",
        "payment_provider": "payway"
    }
]
```

### 2. Create Checkout Session

```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"plan_id": 1}' \
     http://localhost:8000/api/payments/subscriptions/payway_checkout/
```

Response:
```json
{
    "transaction_id": "tran_user_123_plan_1_1234567890",
    "checkout_html": "<html>...</html>"
}
```

### 3. Check Payment Status

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/payments/subscriptions/payment_status/?transaction_id=tran_123456
```

Response:
```json
{
    "payment_id": "tran_123456",
    "status": "succeeded",
    "amount": 29.99,
    "currency": "USD",
    "approval_code": "123456"
}
```

### 4. Refund Payment

```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"transaction_id": "tran_123456", "amount": 10.00}' \
     http://localhost:8000/api/payments/subscriptions/refund_payment/
```

Response:
```json
{
    "refund_id": "ref_123456",
    "status": "succeeded",
    "amount": 10.00
}
```

## Frontend Integration

### React Example

```jsx
// SubscriptionCheckout.jsx
import React, { useState } from 'react';
import axios from 'axios';

function SubscriptionCheckout({ planId }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleCheckout = async () => {
    try {
      setLoading(true);
      const response = await axios.post(
        '/api/payments/subscriptions/payway_checkout/',
        { plan_id: planId },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );
      
      // Render checkout HTML
      const container = document.getElementById('checkout-container');
      container.innerHTML = response.data.checkout_html;
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <button onClick={handleCheckout} disabled={loading}>
        {loading ? 'Loading...' : 'Pay with PayWay'}
      </button>
      {error && <div className="error">{error}</div>}
      <div id="checkout-container"></div>
    </div>
  );
}

export default SubscriptionCheckout;
```

## Troubleshooting

### 1. "Unsupported payment provider: payway"

Ensure PayWay environment variables are set:
```bash
PAYWAY_MERCHANT_ID=your_merchant_id
PAYWAY_API_KEY=your_api_key
PAYWAY_API_SECRET=your_api_secret
PAYWAY_SANDBOX=True
PAYWAY_RETURN_URL=http://localhost:4000/api/payments/payway/callback/
```

### 2. "Invalid webhook signature"

- Verify `PAYWAY_API_SECRET` matches PayWay dashboard
- Check webhook URL is whitelisted in merchant profile
- Ensure request body is raw bytes, not parsed JSON

### 3. Payment not marked as paid

- Check if callback webhook is being received
- Verify transaction was created correctly
- Check PayWay transaction logs in dashboard

## References

- [PayWay Developer Docs](https://developer.payway.com.kh/)
- [PayWay Dashboard](https://dashboard.payway.com.kh/)
- [OmniPayments Framework](../../omnipayments/README.md)
