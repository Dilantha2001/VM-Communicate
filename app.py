from flask import Flask, request, jsonify, render_template
from datetime import datetime
import json
import os

app = Flask(__name__)

# Store messages in memory (persists while server runs)
messages = []


OTHER_VM_URL = "http://16.171.32.145:5000"  
CURRENT_VM_ID = "VM1"  
@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template('index.html', vm_id=CURRENT_VM_ID)

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Fetch all messages"""
    return jsonify({
        'messages': messages,
        'count': len(messages)
    })

@app.route('/api/messages', methods=['POST'])
def post_message():
    """Receive a message from the other VM or this user"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Invalid message'}), 400
    
    message = {
        'id': len(messages) + 1,
        'sender': data.get('sender', 'Unknown'),
        'text': data['text'],
        'timestamp': datetime.now().isoformat(),
        'source_vm': data.get('source_vm', CURRENT_VM_ID)
    }
    
    messages.append(message)
    
    # Forward message to the other VM
    try:
        if data.get('source_vm') != 'OTHER':  # Avoid infinite loops
            forward_to_other_vm(message)
    except Exception as e:
        print(f"Could not forward message: {e}")
    
    return jsonify({
        'success': True,
        'message': message
    }), 201

@app.route('/api/messages', methods=['DELETE'])
def clear_messages():
    """Clear all messages"""
    global messages
    messages = []
    return jsonify({'success': True, 'message': 'Messages cleared'})

def forward_to_other_vm(message):
    """Send message to the other VM"""
    import requests
    try:
        payload = {
            'sender': message['sender'],
            'text': message['text'],
            'timestamp': message['timestamp'],
            'source_vm': 'OTHER'
        }
        response = requests.post(
            f"{OTHER_VM_URL}/api/messages",
            json=payload,
            timeout=5
        )
        return response.status_code == 201
    except requests.exceptions.RequestException as e:
        print(f"Error forwarding message: {e}")
        return False

@app.route('/api/status', methods=['GET'])
def status():
    """Check if server is running and other VM status"""
    import requests
    
    other_vm_status = "offline"
    try:
        response = requests.get(f"{OTHER_VM_URL}/api/status", timeout=2)
        if response.status_code == 200:
            other_vm_status = "online"
    except:
        other_vm_status = "offline"
    
    return jsonify({
        'current_vm': CURRENT_VM_ID,
        'status': 'online',
        'other_vm': other_vm_status,
        'message_count': len(messages)
    })

if __name__ == '__main__':
    # Enable CORS for cross-VM communication
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        return response
    
    # Run on all network interfaces so it's accessible from other VMs
    app.run(host='0.0.0.0', port=5000, debug=False)