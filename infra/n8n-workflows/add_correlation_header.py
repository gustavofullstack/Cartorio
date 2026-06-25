#!/usr/bin/env python3
"""
Script to add X-Correlation-ID header to all HTTP Request nodes in N8N workflows.

B09: Structured JSON logs with correlation_id in all N8N nodes
- Add X-Correlation-ID header to all HTTP Request nodes
- Ensure correlation_id from Init Correlation node is passed
"""

import json
import os
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent

def add_correlation_header_to_workflow(wf_path: Path) -> bool:
    """Add X-Correlation-ID header to all HTTP Request nodes in a workflow."""
    try:
        with open(wf_path, 'r') as f:
            wf = json.load(f)
    except Exception as e:
        print(f"  ERROR reading {wf_path.name}: {e}")
        return False

    modified = False
    http_nodes_updated = 0

    for node in wf.get('nodes', []):
        # Check if this is an HTTP Request node
        if node.get('type') == 'n8n-nodes-base.httpRequest':
            params = node.get('parameters', {})
            header_params = params.get('headerParameters', {})
            parameters_list = header_params.get('parameters', [])

            # Check if X-Correlation-ID already exists
            has_correlation_header = any(
                p.get('name') == 'X-Correlation-ID' for p in parameters_list
            )

            if not has_correlation_header:
                # Add X-Correlation-ID header
                parameters_list.append({
                    "name": "X-Correlation-ID",
                    "value": "={{ $json.correlation_id }}"
                })
                http_nodes_updated += 1
                modified = True
                print(f"    Added X-Correlation-ID to node: {node.get('name')}")

    if modified:
        # Backup original
        backup_path = wf_path.with_suffix('.json.bak')
        with open(backup_path, 'w') as f:
            json.dump(wf, f, indent=2)
        
        # Write updated workflow
        with open(wf_path, 'w') as f:
            json.dump(wf, f, indent=2)
        
        print(f"  UPDATED {wf_path.name}: {http_nodes_updated} HTTP nodes updated")
        return True
    else:
        print(f"  SKIP {wf_path.name}: already has X-Correlation-ID headers")
        return False


def main():
    print("=" * 60)
    print("B09: Adding X-Correlation-ID header to all HTTP Request nodes")
    print("=" * 60)
    
    workflow_files = sorted(WORKFLOWS_DIR.glob('*.json'))
    workflow_files = [f for f in workflow_files if not f.name.endswith('.bak')]
    
    updated_count = 0
    total_http_nodes = 0
    
    for wf_file in workflow_files:
        print(f"\nProcessing: {wf_file.name}")
        # Try to read and check if it has HTTP Request nodes
        try:
            with open(wf_file, 'r') as f:
                wf = json.load(f)
        except:
            print(f"  ERROR: Could not parse JSON")
            continue
        
        # Check if workflow has HTTP Request nodes
        http_nodes = [n for n in wf.get('nodes', []) if n.get('type') == 'n8n-nodes-base.httpRequest']
        if not http_nodes:
            print(f"  SKIP: No HTTP Request nodes")
            continue
        
        print(f"  Found {len(http_nodes)} HTTP Request nodes")
        if add_correlation_header_to_workflow(wf_file):
            updated_count += 1
            total_http_nodes += len(http_nodes)
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: {updated_count} workflows updated, {total_http_nodes} total HTTP nodes")
    print("=" * 60)


if __name__ == '__main__':
    main()