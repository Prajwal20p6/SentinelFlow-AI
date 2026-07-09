# SentinelFlow AI — Demonstration Scripts & Scenarios

This guide outlines how to run a complete, high-fidelity demonstration of SentinelFlow AI.

---

## 1. Scenario Configurations

SentinelFlow AI supports three pre-configured, deterministic scenarios inside the demo console:

1. **CPU Exhaustion (Autopilot Bypass)**:
   - **Scenario**: CPU usage spikes above 95% on a node.
   - **Remediation**: Recommends scaling replicas. Confidence is evaluated below the 80% threshold (e.g. 75%), routing the ticket to state `PENDING_APPROVAL`.
   - **Demonstrates**: Human-in-the-loop (HITL) approval gates, Slack interactive buttons, and state transition updates.
2. **Storage Exhaustion (Auto-Heal)**:
   - **Scenario**: Persistent Volume disk usage reaches 95%.
   - **Remediation**: Recommends deleting old diagnostic log files. Confidence is high (e.g. 85%), triggering automatic execution (state transitions to `EXECUTED`).
   - **Demonstrates**: Autopilot healing, dry-run command logging, and verification.
3. **Security Intrusion (Safety Block)**:
   - **Scenario**: Unauthorized scan attempts detected from a foreign namespace.
   - **Remediation**: Suggests blocking network access, but attempts to inject a dangerous deletion command (`rm -rf /etc/kubernetes/manifests`).
   - **Demonstrates**: Input injection guardrails, Enkrypt policy blocks, and instant threat warnings.

---

## 2. Walkthrough Script (Step-by-Step)

### Prep
1. Ensure services are running locally via `.\start.ps1`.
2. Open the React Dashboard at `http://localhost:3000`.

### Step 1: Human-in-the-Loop Approval Demo
1. Navigate to the **Settings** panel on the left navigation bar.
2. Under the "Simulation Triggers" block, click **Trigger CPU Spike**.
3. Go back to the **Incidents Queue** tab.
4. Observe a new incident ticket appears immediately. The status is `PENDING_APPROVAL` and the details show:
   * "Incident requires manual approval. Confidence is below threshold: 75%".
5. Navigate to the **Slack Alerts** simulator widget.
6. Click **Approve Action** under the active alert.
7. Observe the incident status transitions in real-time to `EXECUTED`, and the Command Output prints the scaled Kubernetes deployment.

### Step 2: Auto-Healing Demo
1. Navigate to the **Settings** panel.
2. Click **Trigger Disk Full**.
3. Go back to the **Incidents Queue** tab.
4. Observe the incident transitions instantly to `EXECUTED`. The timeline shows the autopilot confidence gate auto-approved the suggested rollback commands.

### Step 3: Security Injection Block Demo
1. Open the **Guarded Manual Console** inside the Dashboard.
2. Type: `rm -rf /var/run/secrets/` and press enter.
3. Observe the console prints a bright red critical risk warning:
   * "Blocked: Command matches safety policy blacklist rule".
4. Navigate to the **Safety Audits Ledger** tab, verifying the block trail was written as a cryptographic hash block.
