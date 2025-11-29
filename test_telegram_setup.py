import requests

def verify_bot_token(token):
    """Verify if a bot token is valid"""
    url = f"https://api.telegram.org/bot8476901681:AAEFkXR4quyhNkGLxle47reh7Hn5OxQIU7I/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["ok"]:
            bot_info = data["result"]
            print(f"✅ Bot token is VALID!")
            print(f"🤖 Bot Name: {bot_info.get('first_name')}")
            print(f"👤 Username: @{bot_info.get('username')}")
            return True
        else:
            print(f"❌ Invalid token: {data.get('description')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_chat_id(token):
    """Get your chat ID after sending a message to the bot"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data["ok"] and data["result"]:
            print("📨 Found messages:")
            for update in data["result"]:
                if "message" in update:
                    chat = update["message"]["chat"]
                    print(f"💬 From: {chat.get('first_name', 'Unknown')} (ID: {chat['id']})")
                    return chat["id"]
        else:
            print("❌ No messages found. Please send a message to your bot first.")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

# Test with your current token (replace with new one)
current_token = "8476901681:AAEFkXR4quyhNkGLxle47reh7Hn50xQIU7I"
print("Testing current token...")
verify_bot_token(current_token)

print("\n" + "="*50)
print("INSTRUCTIONS:")
print("1. Create a new bot with @BotFather")
print("2. Replace the token above with your new token")
print("3. Send a message to your new bot")
print("4. Run this script again to get your chat ID")
print("="*50)