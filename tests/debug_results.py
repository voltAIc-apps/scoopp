#!/usr/bin/env python3
"""
Debug utility to analyze result structures and identify nesting issues.
"""
import json

def analyze_structure(obj, path="root", max_depth=5, current_depth=0):
    """
    Analyze the structure of an object and report any nesting issues.
    """
    if current_depth > max_depth:
        return [{"path": path, "issue": "Max depth exceeded", "type": type(obj).__name__}]
    
    issues = []
    
    if isinstance(obj, list):
        print(f"{'  ' * current_depth}{path}: list[{len(obj)}]")
        
        # Check if this is a list of lists (potential issue)
        list_count = sum(1 for item in obj if isinstance(item, list))
        if list_count > 0:
            issues.append({
                "path": path, 
                "issue": f"Contains {list_count} nested lists out of {len(obj)} items",
                "type": "list",
                "severity": "warning" if list_count < len(obj) else "error"
            })
        
        # Analyze first few items
        for i, item in enumerate(obj[:3]):  # Only check first 3 items
            issues.extend(analyze_structure(item, f"{path}[{i}]", max_depth, current_depth + 1))
            
        if len(obj) > 3:
            print(f"{'  ' * (current_depth + 1)}... ({len(obj) - 3} more items)")
    
    elif isinstance(obj, dict):
        print(f"{'  ' * current_depth}{path}: dict with {len(obj)} keys")
        
        # Analyze a few key-value pairs
        for i, (key, value) in enumerate(list(obj.items())[:3]):
            issues.extend(analyze_structure(value, f"{path}.{key}", max_depth, current_depth + 1))
            
        if len(obj) > 3:
            print(f"{'  ' * (current_depth + 1)}... ({len(obj) - 3} more keys)")
    
    else:
        print(f"{'  ' * current_depth}{path}: {type(obj).__name__}")
    
    return issues

def check_result_structure(results):
    """
    Check if results follow the expected List[Dict] structure.
    """
    print("🔍 Analyzing Result Structure")
    print("=" * 40)
    
    if not isinstance(results, list):
        print(f"❌ CRITICAL: Root should be a list, got {type(results)}")
        return False
    
    print(f"✅ Root is a list with {len(results)} items")
    
    issues = analyze_structure(results, "results")
    
    if issues:
        print("\n⚠️  Issues Found:")
        for issue in issues:
            severity_icon = "❌" if issue.get("severity") == "error" else "⚠️"
            print(f"  {severity_icon} {issue['path']}: {issue['issue']}")
        return len([i for i in issues if i.get("severity") == "error"]) == 0
    else:
        print("\n✅ No structural issues found!")
        return True

if __name__ == "__main__":
    # Example usage
    print("Result Structure Analyzer")
    print("This tool helps debug nested list issues in crawler results")
    print("\nTo use:")
    print("1. Save your API response to a JSON file")
    print("2. Run: python debug_results.py < response.json")
    print("3. Or import and use check_result_structure(your_results)")
    
    try:
        import sys
        if not sys.stdin.isatty():  # If there's piped input
            data = json.load(sys.stdin)
            if "results" in data:
                check_result_structure(data["results"])
            else:
                check_result_structure(data)
    except:
        pass