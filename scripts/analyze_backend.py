#!/usr/bin/env python3
"""
WealthFlow Backend Analysis Tool
Run this in the project root directory to analyze backend structure

Usage:
    cd /path/to/wealthflow
    python analyze_backend.py
"""

import re
from pathlib import Path

def analyze_views():
    """Analyze views.py structure"""
    views_file = Path('core/views.py')
    
    if not views_file.exists():
        print("❌ views.py not found in core/ directory")
        return False
    
    with open(views_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all classes
    class_pattern = r'class (\w+)\('
    classes = re.findall(class_pattern, content)
    
    # Find all methods
    method_pattern = r'def (\w+)\(self'
    methods = re.findall(method_pattern, content)
    
    # Count imports
    import_lines = [line for line in content.split('\n') if line.startswith('import ') or line.startswith('from ')]
    
    # File size
    lines = len(content.split('\n'))
    
    print("\n" + "="*70)
    print("📊 VIEWS.PY ANALYSIS REPORT")
    print("="*70)
    print(f"\n📁 Total Lines: {lines}")
    print(f"📦 Total Import Statements: {len(import_lines)}")
    print(f"📋 Total Classes: {len(classes)}")
    print(f"⚙️  Total Methods: {len(methods)}")
    
    print("\n" + "-"*70)
    print("📋 ALL CLASSES FOUND:")
    print("-"*70)
    
    for i, cls in enumerate(classes, 1):
        print(f"{i:2d}. {cls}")
    
    print("\n" + "-"*70)
    print("🔍 IMPORT STATEMENTS (first 30):")
    print("-"*70)
    
    for imp in import_lines[:30]:
        print(f"  {imp}")
    
    if len(import_lines) > 30:
        print(f"\n  ... and {len(import_lines) - 30} more imports")
    
    return True

def analyze_models():
    """Analyze models.py structure"""
    models_file = Path('core/models.py')
    
    if not models_file.exists():
        print("❌ models.py not found in core/ directory")
        return False
    
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all model classes
    model_pattern = r'class (\w+)\(models\.Model\)'
    models = re.findall(model_pattern, content)
    
    lines = len(content.split('\n'))
    
    print("\n" + "="*70)
    print("📊 MODELS.PY ANALYSIS REPORT")
    print("="*70)
    print(f"\n📁 Total Lines: {lines}")
    print(f"📦 Total Models: {len(models)}")
    
    print("\n" + "-"*70)
    print("📋 MODELS FOUND:")
    print("-"*70)
    
    for i, model in enumerate(models, 1):
        print(f"{i:2d}. {model}")
    
    return True

def analyze_urls():
    """Analyze URL patterns"""
    urls_file = Path('core/urls.py')
    
    if not urls_file.exists():
        print("❌ urls.py not found in core/ directory")
        return False
    
    with open(urls_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all path definitions
    path_pattern = r"path\('([^']+)'"
    paths = re.findall(path_pattern, content)
    
    lines = len(content.split('\n'))
    
    print("\n" + "="*70)
    print("📊 URLS.PY ANALYSIS REPORT")
    print("="*70)
    print(f"\n📁 Total Lines: {lines}")
    print(f"🔗 Total URL Patterns: {len(paths)}")
    
    print("\n" + "-"*70)
    print("🔗 URL PATTERNS FOUND (first 40):")
    print("-"*70)
    
    for i, path in enumerate(paths[:40], 1):
        print(f"{i:2d}. /{path}")
    
    if len(paths) > 40:
        print(f"\n... and {len(paths) - 40} more patterns")
    
    return True

def analyze_directory_structure():
    """Show project directory structure"""
    print("\n" + "="*70)
    print("📁 PROJECT DIRECTORY STRUCTURE")
    print("="*70 + "\n")
    
    core_path = Path('core')
    
    if not core_path.exists():
        print("❌ core/ directory not found")
        return False
    
    print("core/ directory contents:")
    for item in sorted(core_path.iterdir()):
        if item.is_file() and item.suffix == '.py':
            size = item.stat().st_size
            lines = len(item.read_text(encoding='utf-8').split('\n'))
            print(f"  ├─ {item.name:30s} ({lines:5d} lines, {size:8d} bytes)")
        elif item.is_dir() and not item.name.startswith('__pycache__'):
            print(f"  ├─ {item.name}/ (directory)")
    
    return True

def generate_report_summary(output_file='BACKEND_ANALYSIS_REPORT.txt'):
    """Generate a text report file"""
    print("\n" + "="*70)
    print("💾 SAVING REPORT TO FILE")
    print("="*70)
    print(f"\nGenerating {output_file}...\n")
    
    # Capture all output
    print(f"✅ Report will be saved to: {output_file}")

def main():
    print("\n" + "🔍 WEALTHFLOW BACKEND STRUCTURE ANALYZER")
    print("="*70)
    print("This tool analyzes your WealthFlow project structure")
    print("Run this from your project root directory\n")
    
    # Check if we're in the right directory
    if not Path('core').exists():
        print("❌ ERROR: core/ directory not found!")
        print("❌ Make sure you're running this from WealthFlow project root")
        print("❌ Current directory:", Path.cwd())
        return
    
    print("✅ Found core/ directory - starting analysis...\n")
    
    # Run all analyses
    success = True
    
    success = analyze_directory_structure() and success
    success = analyze_views() and success
    success = analyze_models() and success
    success = analyze_urls() and success
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE!")
    print("="*70)
    print("\n📋 NEXT STEPS:")
    print("   1. Copy ALL the output above")
    print("   2. Send it to Ehab")
    print("   3. Ehab will create a refactoring plan based on your actual code")
    print("   4. Follow BACKEND_REFACTORING_GUIDE_FOR_ANTIGRAVITY.md")
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
