#!/usr/bin/env python3
"""
Script to parse XML custom field definitions and update polarion_config.yaml.

Usage:
    python scripts/parse_custom_fields.py --xml fields.xml --project dlco --work-item-type regulatoryRequirement
    python scripts/parse_custom_fields.py --xml fields.xml --project dlco --work-item-type regulatoryRequirement --config-file custom_config.yaml
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

from ruamel.yaml import YAML


def parse_xml_custom_fields(xml_content: str) -> List[str]:
    """
    Parse XML custom field definitions and extract field IDs.
    
    Args:
        xml_content: XML content as string
        
    Returns:
        List of custom field IDs
    """
    try:
        root = ET.fromstring(xml_content)
        field_ids = []
        
        # Handle both <fields> root and direct <field> elements
        if root.tag == 'fields':
            fields = root.findall('field')
        else:
            fields = [root] if root.tag == 'field' else []
            
        for field in fields:
            field_id = field.get('id')
            if field_id:
                field_ids.append(field_id)
                
        return field_ids
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format: {e}")


def load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file preserving comments and formatting."""
    yaml = YAML()
    yaml.preserve_quotes = True
    
    if not config_path.exists():
        return {"projects": {}}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f) or {}
            if 'projects' not in config:
                config['projects'] = {}
            return config
    except Exception as e:
        raise ValueError(f"Invalid YAML format in {config_path}: {e}")


def update_config_with_custom_fields(
    config: Dict[str, Any], 
    project_id: str, 
    work_item_type: str, 
    custom_fields: List[str]
) -> Dict[str, Any]:
    """
    Update configuration with custom fields for a specific work item type.
    
    Args:
        config: Current configuration dictionary
        project_id: Project ID
        work_item_type: Work item type name
        custom_fields: List of custom field IDs
        
    Returns:
        Updated configuration dictionary
    """
    # Ensure project exists in config
    if project_id not in config['projects']:
        config['projects'][project_id] = {
            'id': project_id,
            'work_item_types': [],
            'custom_fields': {}
        }
    
    project_config = config['projects'][project_id]
    
    # Ensure custom_fields section exists
    if 'custom_fields' not in project_config:
        project_config['custom_fields'] = {}
    
    # Add work item type to work_item_types list if not present
    if 'work_item_types' not in project_config:
        project_config['work_item_types'] = []
    
    if work_item_type not in project_config['work_item_types']:
        project_config['work_item_types'].append(work_item_type)
    
    # Update custom fields for the work item type
    project_config['custom_fields'][work_item_type] = custom_fields
    
    return config


def save_yaml_config(config: Dict[str, Any], config_path: Path) -> None:
    """Save configuration to YAML file preserving comments and formatting."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    
    # Create backup if file exists
    if config_path.exists():
        backup_path = config_path.with_suffix('.yaml.bak')
        config_path.rename(backup_path)
        print(f"Created backup: {backup_path}")
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f)


def main():
    parser = argparse.ArgumentParser(
        description="Parse XML custom field definitions and update polarion_config.yaml"
    )
    parser.add_argument(
        '--xml', 
        required=True, 
        help='Path to XML file containing custom field definitions'
    )
    parser.add_argument(
        '--project', 
        required=True, 
        help='Project ID (e.g., "dlco")'
    )
    parser.add_argument(
        '--work-item-type', 
        required=True, 
        help='Work item type name (e.g., "regulatoryRequirement")'
    )
    parser.add_argument(
        '--config-file', 
        default='polarion_config.yaml',
        help='Path to polarion_config.yaml file (default: polarion_config.yaml)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be updated without making changes'
    )
    
    args = parser.parse_args()
    
    try:
        # Read XML file
        xml_path = Path(args.xml)
        if not xml_path.exists():
            print(f"❌ XML file not found: {xml_path}")
            sys.exit(1)
            
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        # Parse custom fields
        custom_fields = parse_xml_custom_fields(xml_content)
        if not custom_fields:
            print("❌ No custom fields found in XML")
            sys.exit(1)
            
        print(f"✅ Found {len(custom_fields)} custom fields:")
        for field_id in custom_fields:
            print(f"  - {field_id}")
        
        # Load current config
        config_path = Path(args.config_file)
        config = load_yaml_config(config_path)
        
        # Update config
        updated_config = update_config_with_custom_fields(
            config, args.project, args.work_item_type, custom_fields
        )
        
        if args.dry_run:
            print(f"\n🔍 Dry run - would update {config_path}:")
            print(f"Project: {args.project}")
            print(f"Work item type: {args.work_item_type}")
            print(f"Custom fields: {', '.join(custom_fields)}")
        else:
            # Save updated config
            save_yaml_config(updated_config, config_path)
            print(f"\n✅ Updated {config_path}")
            print(f"Project: {args.project}")
            print(f"Work item type: {args.work_item_type}")
            print(f"Custom fields: {', '.join(custom_fields)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()