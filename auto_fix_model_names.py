#!/usr/bin/env python3
"""
Auto-fix script to update model names in your files
Run this to fix the model name issue
"""

import os

def fix_file(filename):
    """Fix model name in a file"""
    if not os.path.exists(filename):
        print(f"⚠️  {filename} not found, skipping...")
        return False
    
    print(f"\n📝 Fixing {filename}...")
    
    # Read the file
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count occurrences
    old_count = content.count('gemini-1.5-pro')
    
    if old_count == 0:
        print(f"   ✅ Already using correct model name!")
        return True
    
    # Replace all occurrences
    new_content = content.replace('gemini-1.5-pro', 'gemini-2.5-flash')
    new_content = new_content.replace('gemini-pro', 'gemini-2.5-flash')
    
    # Write back
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"   ✅ Fixed! Replaced {old_count} occurrences")
    print(f"   📝 Now using: gemini-2.5-flash")
    return True

def main():
    print("="*60)
    print("🔧 AUTO-FIX: Updating Gemini Model Names")
    print("="*60)
    
    files_to_fix = [
        'test_gemini_setup.py',
        'voice_agent_llm_evaluation.py',
        'voice_agent.py',
        'main.py'
    ]
    
    fixed_count = 0
    for filename in files_to_fix:
        if fix_file(filename):
            fixed_count += 1
    
    print("\n" + "="*60)
    print(f"✅ Fixed {fixed_count} files!")
    print("="*60)
    print("\nrun: python test_gemini_setup.py")
    print()

if __name__ == "__main__":
    main()