"""
FastAPI Example - PayWay Payment Integration
Complete example showing how to integrate PayWay with FastAPI
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from omnipayments import get_provider
from decimal import Decimal
from typing import Optional
import json

app = FastAPI(title="PayWay FastAPI Example")

# Configuration
PAYWAY_CONFIG = {
    'merchant_id': 'your_merchant_id',
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret',
    'sandbox': True,  # Set to False for production
    'return_url': 'http://localhost:8000/payway/callback',
}

# In-memory store for transactions (use database in production)
transactions = {}


@app.get("/payway/checkout/{plan_id}")
async def payway_checkout(plan_id: str, request: Request):
    """Create PayWay checkout session"""
    try:
        # Get PayWay provider
        payway = get_provider('payway', PAYWAY_CONFIG)
        
        # Create checkout session
        session = payway.create_checkout_session(
            amount=Decimal('29.99'),
            currency='USD',
            user_id='user_123',
            plan_id=plan_id,
            success_url=str(request.url_for('payway_success')),
            cancel_url=str(request.url_for('payway_cancel')),
            metadata={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone': '+855123456789',
            }
        )
        
        # Store transaction for verification
        transactions[session['transaction_id']] = session
        
        # Return checkout HTML
        return HTMLResponse(content=session['checkout_html'])
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/payway/callback", name="payway_callback")
async def payway_callback(request: Request):
    """
    PayWay payment callback/webhook endpoint
    
    PayWay sends payment status updates as HTTP POST to this URL
    """
    try:
        # Get callback data from PayWay
        payload = await request.body()
        event_data = await request.json()
        signature = request.headers.get('X-PayWay-Signature', '')
        
        # Get PayWay provider for verification
        payway = get_provider('payway', PAYWAY_CONFIG)
        
        # Verify webhook signature
        is_valid = payway.verify_webhook(
            payload=payload,
            signature=signature,
            secret=PAYWAY_CONFIG['api_secret']
        )
        
        if not is_valid:
            raise ValueError("Invalid webhook signature")
        
        # Process payment status
        result = payway.process_webhook(
            event_type='payment.completed',
            event_data=event_data
        )
        
        # Extract transaction ID and user info
        transaction_id = event_data.get('tran_id')
        status = result.get('status')
        
        # Verify payment status
        if status == 'succeeded':
            # Payment successful - update database, send confirmation email, etc.
            print(f"✅ Payment succeeded: {transaction_id}")
            print(f"Metadata: {result.get('metadata')}")
            
            # TODO: Update subscription in database
            # user = User.objects.get(id=result['metadata']['user_id'])
            # Subscription.objects.create(
            #     user=user,
            #     plan_id=result['metadata']['plan_id'],
            #     payment_provider='payway',
            #     provider_transaction_id=transaction_id
            # )
        
        elif status == 'failed':
            print(f"❌ Payment failed: {transaction_id}")
            print(f"Error: {result.get('error')}")
            # TODO: Log payment failure
        
        return JSONResponse({'status': 'processed'})
    
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/payway/success", name="payway_success")
async def payway_success(request: Request):
    """Redirect page after successful payment"""
    return HTMLResponse("""
    <html>
    <body>
        <h1>✅ Payment Successful!</h1>
        <p>Your subscription has been activated.</p>
        <a href="/">Back to Dashboard</a>
    </body>
    </html>
    """)


@app.get("/payway/cancel", name="payway_cancel")
async def payway_cancel(request: Request):
    """Redirect page if payment is cancelled"""
    return HTMLResponse("""
    <html>
    <body>
        <h1>❌ Payment Cancelled</h1>
        <p>Your payment was not processed. Please try again.</p>
        <a href="/payway/checkout/plan_1">Retry Payment</a>
    </body>
    </html>
    """)


@app.get("/payway/status/{transaction_id}")
async def payway_status(transaction_id: str):
    """Check payment status"""
    try:
        payway = get_provider('payway', PAYWAY_CONFIG)
        
        # Get payment status from PayWay
        status = payway.get_payment_status(transaction_id)
        
        return JSONResponse(status)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/payway/refund/{transaction_id}")
async def payway_refund(transaction_id: str, request: Request):
    """Refund a payment"""
    try:
        data = await request.json()
        refund_amount = data.get('amount')
        
        payway = get_provider('payway', PAYWAY_CONFIG)
        
        # Refund payment
        refund = payway.refund_payment(
            payment_id=transaction_id,
            amount=Decimal(refund_amount) if refund_amount else None
        )
        
        return JSONResponse(refund)
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Demo page to test payment flow
@app.get("/", response_class=HTMLResponse)
async def index():
    """Demo page"""
    return """
    <html>
    <head>
        <title>PayWay Integration Demo</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; }
            .button { 
                display: inline-block; 
                padding: 10px 20px; 
                margin: 5px; 
                background-color: #007bff; 
                color: white; 
                text-decoration: none; 
                border-radius: 5px;
                cursor: pointer;
            }
            .button:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <h1>PayWay Payment Integration</h1>
        
        <h2>Test Payment</h2>
        <p>
            <a href="/payway/checkout/plan_1" class="button">Start Payment (USD 29.99)</a>
        </p>
        
        <h2>Test Cards (Sandbox)</h2>
        <table border="1" cellpadding="10">
            <tr>
                <th>Card Number</th>
                <th>Result</th>
                <th>Expiry</th>
                <th>CVV</th>
            </tr>
            <tr>
                <td>4000 0000 0000 0002</td>
                <td>Success</td>
                <td>Any future date</td>
                <td>Any 3 digits</td>
            </tr>
            <tr>
                <td>4000 0000 0000 0009</td>
                <td>Failure</td>
                <td>Any future date</td>
                <td>Any 3 digits</td>
            </tr>
        </table>
        
        <h2>API Endpoints</h2>
        <ul>
            <li><strong>POST</strong> /payway/checkout/{plan_id} - Create checkout</li>
            <li><strong>POST</strong> /payway/callback - Webhook endpoint (called by PayWay)</li>
            <li><strong>GET</strong> /payway/status/{transaction_id} - Check payment status</li>
            <li><strong>POST</strong> /payway/refund/{transaction_id} - Refund payment</li>
        </ul>
    </body>
    </html>
    """


if __name__ == '__main__':
    import uvicorn
    print("🚀 Starting FastAPI with PayWay integration...")
    print("📍 Open http://localhost:8000 in your browser")
    print("⚙️ Configure PAYWAY_CONFIG with your credentials")
    uvicorn.run(app, host='0.0.0.0', port=8000)
