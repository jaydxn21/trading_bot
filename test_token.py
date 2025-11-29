# test_token.py - TEST YOUR DERIV TOKEN
import websocket
import json
import time

def test_deriv_token(token, app_id):
    print(f"🔍 Testing token: {token} with app_id: {app_id}")
    
    def on_message(ws, message):
        data = json.loads(message)
        print("📨 RESPONSE:", data)
        
        if data.get("msg_type") == "authorization":
            auth = data.get("authorization", {})
            if auth.get("token"):
                print("✅ SUCCESS: Token is VALID!")
                print(f"   Account: {auth.get('loginid')}")
                print(f"   Currency: {auth.get('currency')}")
                print(f"   Country: {auth.get('country')}")
            else:
                error = data.get("error", {})
                print(f"❌ FAILED: {error.get('code')} - {error.get('message')}")
        
        ws.close()
    
    def on_error(ws, error):
        print(f"❌ WebSocket Error: {error}")
    
    def on_close(ws, *args):
        print("🔒 Connection closed")
    
    def on_open(ws):
        print("🔗 Connected - Sending authentication...")
        ws.send(json.dumps({"authorize": token}))
    
    ws = websocket.WebSocketApp(
        f"wss://ws.derivws.com/websockets/v3?app_id={app_id}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    print("🚀 Starting test...")
    ws.run_forever()

# Test your current token
test_deriv_token("TJjpI6X4ymSI4xg", "111074")