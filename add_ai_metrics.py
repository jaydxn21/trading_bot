#!/usr/bin/env python3
import re

# Read the bot.py file
with open('bot.py', 'r') as f:
    content = f.read()

# Find the system summary method and add AI metrics
summary_pattern = r"def broadcast_system_summary\(self\):"
summary_match = re.search(summary_pattern, content)

if summary_match:
    # Find the summary dictionary in the method
    summary_dict_pattern = r"summary = \{"
    summary_dict_match = re.search(summary_dict_pattern, content[summary_match.start():])
    
    if summary_dict_match:
        # Calculate the position where we should insert AI metrics
        insert_pos = summary_match.start() + summary_dict_match.end()
        
        # Find the end of the summary dictionary (look for the closing brace with proper indentation)
        current_pos = insert_pos
        brace_count = 1
        while brace_count > 0 and current_pos < len(content):
            if content[current_pos] == '{':
                brace_count += 1
            elif content[current_pos] == '}':
                brace_count -= 1
            current_pos += 1
        
        if brace_count == 0:
            # Insert AI metrics before the closing brace
            ai_metrics = '''
            # AI Metrics
            'ai_metrics': {
                'ml_model_trained': self.ml_predictor.is_trained,
                'training_samples': len(self.ml_predictor.training_data),
                'learning_mode': self.learning_mode,
                'ai_optimizer_available': self.ai_optimizer is not None
            },'''
            
            content = content[:current_pos-1] + ai_metrics + '\\n        }' + content[current_pos:]
            print("✅ Added AI metrics to system summary")
        else:
            print("❌ Could not find proper summary dictionary structure")
    else:
        print("❌ Could not find summary dictionary")
else:
    print("❌ Could not find broadcast_system_summary method")

# Write the updated content
with open('bot.py', 'w') as f:
    f.write(content)
