#!/usr/bin/env python3

# Read the bot.py file
with open('bot.py', 'r') as f:
    content = f.read()

# Find where to insert the method (after ai_enhanced_execute_trade method)
insert_after = 'def ai_enhanced_execute_trade(self, strategy: str, action: str, price: float,'
insert_point = content.find(insert_after)

if insert_point != -1:
    # Find the end of the ai_enhanced_execute_trade method
    method_end = content.find('def ', insert_point + len(insert_after))
    if method_end == -1:
        method_end = len(content)
    
    # Insert the missing method after ai_enhanced_execute_trade
    new_method = '''
    def _calculate_position_size(self, confidence: float) -> float:
        """Calculate position size based on confidence (simplified)"""
        base_size = 1.0  # $1 base
        return base_size * (confidence / 100.0)  # Scale with confidence
'''
    
    # Insert the new method
    content = content[:method_end] + new_method + content[method_end:]
    print("✅ Added missing _calculate_position_size method")
else:
    print("❌ Could not find insertion point for _calculate_position_size method")

# Write the updated content
with open('bot.py', 'w') as f:
    f.write(content)
