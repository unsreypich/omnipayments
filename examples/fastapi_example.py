"""
FastAPI Example - Using OmniPayments
"""
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from omnipayments import get_provider
from decimal import Decimal
from typing import Optional
import json

app = FastAPI(title="OmniPayments FastAPI Example")

# Configuration
STRIPE_CONFIG = {
    'secret_key': 'sk_test_...',
    'publishable_key': 'pk_test_...',
    'webhook_secret': 'whsec_...',
}

BAKONG_CONFIG = {
    'merchant_id': 'your_merchant_id',
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret',
    'use_sandbox': True,
}


# Stripe Checkout
@app.get("/checkout/stripe/{plan_id}")
async def stripe_checkout(plan_id: str, request: Request):
    provider = get_provider('stripe', STRIPE_CONFIG)
    
    session = provider.create_checkout_session(
        amount=Decimal('29.99'),
        currency='USD',
        user_id='user_123',  # Get from auth
        plan_id=plan_id,
        success_url=str(request.base_url) + 'success',
        cancel_url=str(request.base_url) + 'cancel',
    )
    
    return RedirectResponse(session['session_url'])


# Bakong KHQR Checkout
@app.get("/checkout/bakong/{plan_id}")
async def bakong_checkout(plan_id: str, request: Request):
    provider = get_provider('bakong', BAKONG_CONFIG)
    
    payment = provider.create_checkout_session(
        amount=Decimal('119600'),  # ~$30 in KHR
        currency='KHR',
        user_id='user_123',
        plan_id=plan_id,
        success_url=str(request.base_url) + 'success',
        cancel_url=str(request.base_url) + 'cancel',
    )
    
    # Display QR code
    html_content = f'''
        <!DOCTYPE html>
        <html>
        <head><title>Scan to Pay</title></head>
        <body style="text-align: center; padding: 50px;">
            <h1>Scan KHQR to Pay</h1>
            <img src="data:image/png;base64,{payment['qr_code']}" style="width: 300px;" />
            <p>Scan with any Cambodian banking app</p>
        </body>
        </html>
    '''
    return HTMLResponse(content=html_content)


# Stripe Webhook
@app.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None)
):
    provider = get_provider('stripe', STRIPE_CONFIG)
    
    payload = await request.body()
    
    if not provider.verify_webhook(payload, stripe_signature, STRIPE_CONFIG['webhook_secret']):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event = await request.json()
    result = provider.process_webhook(event['type'], event['data']['object'])
    
    # Handle the event (update database, send emails, etc.)
    print(f"Processed event: {event['type']}")
    
    return result


# Bakong Webhook
@app.post("/webhooks/bakong")
async def bakong_webhook(
    request: Request,
    x_bakong_signature: Optional[str] = Header(None)
):
    provider = get_provider('bakong', BAKONG_CONFIG)
    
    payload = await request.body()
    
    if not provider.verify_webhook(payload, x_bakong_signature, BAKONG_CONFIG.get('webhook_secret')):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event = await request.json()
    result = provider.process_webhook(event['type'], event['data'])
    
    # Handle the event
    print(f"Processed event: {event['type']}")
    
    return result


# Success/Cancel pages
@app.get("/success")
async def success():
    return HTMLResponse('<h1>Payment Successful!</h1><p>Thank you for your purchase.</p>')

@app.get("/cancel")
async def cancel():
    return HTMLResponse('<h1>Payment Cancelled</h1><p>You can try again.</p>')


# Health check
@app.get("/")
async def root():
    return {
        "message": "OmniPayments FastAPI Example",
        "providers": ["stripe", "bakong"],
        "endpoints": ["/checkout/stripe/{plan_id}", "/checkout/bakong/{plan_id}"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
