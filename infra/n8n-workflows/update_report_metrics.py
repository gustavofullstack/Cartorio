#!/usr/bin/env python3
"""
Script to update "Report Metrics N8N" node in all workflows to send proper
Prometheus metrics per WF (B10).

B10: Prometheus metrics per WF (count, latency, error rate)
- wf_executions_total{workflow, status}
- wf_execution_duration_seconds{workflow}
- wf_errors_total{workflow, error_type}
"""

import json
import os
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent

# New canonical payload for Report Metrics N8N node
NEW_JSON_BODY = """={
  "source": "n8n",
  "wf_name": $workflow.name,
  "wf_id": $workflow.id,
  "execution_id": $execution.id,
  "correlation_id": $json.correlation_id ?? $workflow.id + ':' + $execution.id,
  "status": $execution.success ? 'success' : 'error',
  "duration_seconds": $now.diff($json.wf_started_at, 'seconds'),
  "counters": {
    "n8n_wf_executions_total": {
      "workflow=$workflow.name|status=success": $execution.success ? 1 : 0,
      "workflow=$workflow.name|status=error": $execution.success ? 0 : 1
    },
    "n8n_wf_errors_total": {
      "workflow=$workflow.name|error_type=generic": $execution.success ? 0 : 1
    }
  },
  "gauges": {
    "n8n_wf_execution_duration_seconds": {
      "workflow=$workflow.name": $now.diff($json.wf_started_at, 'seconds')
    }
  },
  "uptime_seconds": $now.diff($json.wf_started_at, 'seconds')
}"""

def update_report_metrics_node(wf_path: Path) -> bool:
    """Update the Report Metrics N8N node in a workflow."""
    try:
        with open(wf_path, 'r') as f:
            wf = json.load(f)
    except Exception as e:
        print(f"  ERROR reading {wf_path.name}: {e}")
        return False

    modified = False
    node_updated = False

    for node in wf.get('nodes', []):
        if node.get('name') == 'Report Metrics N8N':
            params = node.get('parameters', {})
            
            # Update jsonBody
            old_body = params.get('jsonBody', '')
            if 'n8n_wf_executions_total' in old_body and 'workflow=' in old_body:
                # Check if it's already the new format
                if 'n8n_wf_execution_duration_seconds' in old_body:
                    print(f"  SKIP {node.get('name')}: already updated")
                    return False
            
            params['jsonBody'] = NEW_JSON_BODY
            modified = True
            node_updated = True
            print(f"  Updated Report Metrics N8N node in {wf_path.name}")

    if modified:
        # Backup original
        backup_path = wf_path.with_suffix('.json.bak2')
        with open(backup_path, 'w') as f:
            json.dump(wf, f, indent=2)
        
        # Write updated workflow
        with open(wf_path, 'w') as f:
            json.dump(wf, f, indent=2)
        
        return True
    else:
        # Check if there's no Report Metrics N8N node
        has_node = any(n.get('name') == 'Report Metrics N8N' for n in wf.get('nodes', []))
        if not has_node:
            print(f"  SKIP {wf_path.name}: no Report Metrics N8N node")
        return False


def main():
    print("=" * 60)
    print("B10: Updating Report Metrics N8N nodes for per-WF Prometheus metrics")
    print("=" * 60)
    
    workflow_files = sorted(WORKFLOWS_DIR.glob('*.json'))
    workflow_files = [f for f in workflow_files if not f.name.endswith('.bak') and not f.name.endswith('.bak2')]
    
    updated_count = 0
    
    for wf_file in workflow_files:
        # Skip non-workflow JSON files
        if wf_file.name in ['AUDIT_2026-06-24.md', 'CHANGELOG.md', 'M2_6_INJECT_STATUS.md', 'M2_9_DBHOST_FIX.md', 'MIGRATION.md', 'README-error-handler.md', 'README-retry-policy.md', 'README.md', 'WF07_DIAGNOSIS_2026-06-24.md', 'import_all_to_n8n.sh', 'migra-workflows-v1-to-v2.sh']:
            continue
        
        print(f"\nProcessing: {wf_file.name}")
        if update_report_metrics_node(wf_file):
            updated_count += 1
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: {updated_count} workflows updated")
    print("=" * 60)


if __name__ == '__main__':
    main()