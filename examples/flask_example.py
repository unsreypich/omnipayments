"""
Flask Example - Using OmniPayments
"""
from flask import Flask, redirect, request, jsonify, render_template_string
from omnipayments import get_provider
from decimal import Decimal

app = Flask(__name__)

# Configuration
app.config['STRIPE_CONFIG'] = {
    'secret_key': 'sk_test_...',
    'publishable_key': 'pk_test_...',
    'webhook_secret': 'whsec_...',
}

app.config['BAKONG_CONFIG'] = {
    'merchant_id': 'your_merchant_id',
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret',
    'use_sandbox': True,
}

# Stripe Checkout
@app.route('/checkout/stripe/<plan_id>')
def stripe_checkout(plan_id):
    provider = get_provider('stripe', app.config['STRIPE_CONFIG'])
    
    session = provider.create_checkout_session(
        amount=Decimal('29.99'),
        currency='USD',
        user_id='user_123',  # Get from session
        plan_id=plan_id,
        success_url=request.url_root + 'success',
        cancel_url=request.url_root + 'cancel',
    )
    
    return redirect(session['session_url'])


# Bakong KHQR Checkout
@app.route('/checkout/bakong/<plan_id>')
def bakong_checkout(plan_id):
    provider = get_provider('bakong', app.config['BAKONG_CONFIG'])
    
    payment = provider.create_checkout_session(
        amount=Decimal('119600'),  # ~$30 in KHR
        currency='KHR',
        user_id='user_123',
        plan_id=plan_id,
        success_url=request.url_root + 'success',
        cancel_url=request.url_root + 'cancel',
    )
    
    # Display QR code
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head><title>Scan to Pay</title></head>
        <body style="text-align: center; padding: 50px;">
            <h1>Scan KHQR to Pay</h1>
            <img src="data:image/png;base64,{{ qr_code }}" style="width: 300px;" />
            <p>Scan with any Cambodian banking app</p>
        </body>
        </html>
    ''', qr_code=payment['qr_code'])


# Stripe Webhook
@app.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    provider = get_provider('stripe', app.config['STRIPE_CONFIG'])
    
    payload = request.data
    signature = request.headers.get('Stripe-Signature')
    
    if not provider.verify_webhook(payload, signature, app.config['STRIPE_CONFIG']['webhook_secret']):
        return jsonify({'error': 'Invalid signature'}), 400
    
    event = request.get_json()
    result = provider.process_webhook(event['type'], event['data']['object'])
    
    # Handle the event (update database, send emails, etc.)
    print(f"Processed event: {event['type']}")
    
    return jsonify(result)


# Success/Cancel pages
@app.route('/success')
def success():
    return '<h1>Payment Successful!</h1><p>Thank you for your purchase.</p>'

@app.route('/cancel')
def cancel():
    return '<h1>Payment Cancelled</h1><p>You can try again.</p>'


if __name__ == '__main__':
    app.run(debug=True)
