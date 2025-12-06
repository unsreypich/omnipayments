"""
Flask Example - PayWay Payment Integration
Complete example showing how to integrate PayWay with Flask
"""
from flask import Flask, redirect, request, jsonify, render_template_string
from omnipayments import get_provider
from decimal import Decimal
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Configuration
PAYWAY_CONFIG = {
    'merchant_id': 'your_merchant_id',
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret',
    'sandbox': True,  # Set to False for production
    'return_url': 'http://localhost:5000/payway/callback',
}

# In-memory store for transactions (use database in production)
transactions = {}


@app.route('/payway/checkout/<plan_id>')
def payway_checkout(plan_id):
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
            success_url=request.url_root + 'payway/success',
            cancel_url=request.url_root + 'payway/cancel',
            metadata={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone': '+855123456789',
            }
        )
        
        # Store transaction for verification
        transactions[session['transaction_id']] = session
        
        # Render checkout HTML
        return session['checkout_html']
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/payway/callback', methods=['POST'])
def payway_callback():
    """
    PayWay payment callback/webhook endpoint
    
    PayWay sends payment status updates as HTTP POST to this URL
    """
    try:
        # Get callback data from PayWay
        payload = request.get_data()
        event_data = request.get_json()
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
            # user = User.query.get(result['metadata']['user_id'])
            # db.session.add(Subscription(
            #     user_id=user.id,
            #     plan_id=result['metadata']['plan_id'],
            #     payment_provider='payway',
            #     provider_transaction_id=transaction_id
            # ))
            # db.session.commit()
        
        elif status == 'failed':
            print(f"❌ Payment failed: {transaction_id}")
            print(f"Error: {result.get('error')}")
            # TODO: Log payment failure
        
        return jsonify({'status': 'processed'}), 200
    
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 400


@app.route('/payway/success')
def payway_success():
    """Redirect page after successful payment"""
    return render_template_string("""
    <html>
    <body>
        <h1>✅ Payment Successful!</h1>
        <p>Your subscription has been activated.</p>
        <a href="/">Back to Dashboard</a>
    </body>
    </html>
    """)


@app.route('/payway/cancel')
def payway_cancel():
    """Redirect page if payment is cancelled"""
    return render_template_string("""
    <html>
    <body>
        <h1>❌ Payment Cancelled</h1>
        <p>Your payment was not processed. Please try again.</p>
        <a href="/payway/checkout/plan_1">Retry Payment</a>
    </body>
    </html>
    """)


@app.route('/payway/status/<transaction_id>')
def payway_status(transaction_id):
    """Check payment status"""
    try:
        payway = get_provider('payway', PAYWAY_CONFIG)
        
        # Get payment status from PayWay
        status = payway.get_payment_status(transaction_id)
        
        return jsonify(status)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/payway/refund/<transaction_id>', methods=['POST'])
def payway_refund(transaction_id):
    """Refund a payment"""
    try:
        data = request.get_json()
        refund_amount = data.get('amount')
        
        payway = get_provider('payway', PAYWAY_CONFIG)
        
        # Refund payment
        refund = payway.refund_payment(
            payment_id=transaction_id,
            amount=Decimal(refund_amount) if refund_amount else None
        )
        
        return jsonify(refund)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Demo page to test payment flow
@app.route('/')
def index():
    """Demo page"""
    return render_template_string("""
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
            <li><strong>GET</strong> /payway/checkout/{plan_id} - Create checkout</li>
            <li><strong>POST</strong> /payway/callback - Webhook endpoint (called by PayWay)</li>
            <li><strong>GET</strong> /payway/status/{transaction_id} - Check payment status</li>
            <li><strong>POST</strong> /payway/refund/{transaction_id} - Refund payment</li>
        </ul>
    </body>
    </html>
    """)


if __name__ == '__main__':
    print("🚀 Starting Flask with PayWay integration...")
    print("📍 Open http://localhost:5000 in your browser")
    print("⚙️ Configure PAYWAY_CONFIG with your credentials")
    app.run(debug=True, port=5000)
