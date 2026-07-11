import { Workflow, createStep } from "@mastra/core/workflows";
import { rcaAgent, threatIntelAgent, remediationAgent, prioritizationAgent } from "../agents";

interface IncidentData {
  incident_id: string;
  incident_type: string;
  alert_data: Record<string, unknown>;
  metrics: Record<string, unknown>;
  logs: unknown[];
}

export const incidentResponseWorkflow = new Workflow({
  id: "IncidentResponseWorkflow",
  description: "Complete incident response workflow using Mastra agents",
  options: {
    sharePubsub: true
  }
});

// ── Simulation Fallback Generators ──────────────────────────
function getMockRca(incident_type: string) {
  const type = (incident_type || "").toUpperCase();
  if (type === "CPU_SPIKE") {
    return {
      root_cause: "High CPU utilization detected on node-02/api-gateway pod. Scale deployment to mitigate.",
      confidence: 95,
      evidence: ["CPU usage at 98%", "Pod node scheduling latency increased"],
      similar_incidents: ["INC-392", "INC-105"]
    };
  } else if (type === "DISK_FULL") {
    return {
      root_cause: "Storage space exceeded 95% on infrastructure node-03. Clear persistent volume cache.",
      confidence: 90,
      evidence: ["Disk capacity alert at 96% of 500GB volume"],
      similar_incidents: ["INC-204"]
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    return {
      root_cause: "Repeated failed SSH login attempts detected from unrecognized host IP 198.51.100.42.",
      confidence: 98,
      evidence: ["IP 198.51.100.42 attempted 45 failed login attempts in 2 minutes"],
      similar_incidents: ["INC-881"]
    };
  } else if (type === "PHISHING_ATTACK") {
    return {
      root_cause: "Simulated Office 365 phishing breach. PowerShell running, unusual logins from 103.45.67.12, database exfiltration.",
      confidence: 94,
      evidence: ["Unusual login from IP 103.45.67.12", "Malicious PowerShell download execution"],
      similar_incidents: []
    };
  } else if (type === "DDOS_ATTACK") {
    return {
      root_cause: "Traffic volume surge of 15,000 req/sec from botnet IPs 185.120.45.99.",
      confidence: 97,
      evidence: ["Ingress traffic surge of 400%", "Botnet source IP identified in blocklists"],
      similar_incidents: ["INC-129"]
    };
  } else {
    return {
      root_cause: "Impossible travel login detected, database bulk download attempt from IP 99.88.77.66.",
      confidence: 95,
      evidence: ["Login from 99.88.77.66, bulk database download command matched"],
      similar_incidents: ["INC-773"]
    };
  }
}

function getMockThreat(incident_type: string) {
  const type = (incident_type || "").toUpperCase();
  if (type === "CPU_SPIKE" || type === "DISK_FULL") {
    return {
      threat_level: "low",
      risk_score: 10,
      iocs_found: [],
      recommendations: ["Monitor capacity metrics"]
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    return {
      threat_level: "critical",
      risk_score: 92,
      iocs_found: ["198.51.100.42"],
      recommendations: ["Block IP 198.51.100.42 at edge firewall"]
    };
  } else if (type === "PHISHING_ATTACK") {
    return {
      threat_level: "high",
      risk_score: 85,
      iocs_found: ["103.45.67.12"],
      recommendations: ["Revoke session tokens", "Enforce MFA re-enrollment"]
    };
  } else if (type === "DDOS_ATTACK") {
    return {
      threat_level: "critical",
      risk_score: 95,
      iocs_found: ["185.120.45.99"],
      recommendations: ["Apply rate-limiting rules", "Enable cloudflare proxy shielding"]
    };
  } else {
    return {
      threat_level: "critical",
      risk_score: 88,
      iocs_found: ["99.88.77.66"],
      recommendations: ["Apply Kubernetes network policy isolation", "Isolate compromised pod"]
    };
  }
}

function getMockPriority(incident_type: string) {
  const type = (incident_type || "").toUpperCase();
  if (type === "CPU_SPIKE") {
    return {
      priority_level: "P1",
      sla_minutes: 30,
      justification: "Critical API gateway performance degradation",
      business_impact: { affected_users: 1500, risk: "HIGH" }
    };
  } else if (type === "DISK_FULL") {
    return {
      priority_level: "P2",
      sla_minutes: 60,
      justification: "PostgreSQL storage pool pressure warning",
      business_impact: { affected_users: 200, risk: "MEDIUM" }
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    return {
      priority_level: "P0",
      sla_minutes: 15,
      justification: "Active server brute force infiltration attempt",
      business_impact: { affected_users: 5000, risk: "CRITICAL" }
    };
  } else {
    return {
      priority_level: "P0",
      sla_minutes: 15,
      justification: "Potential data exfiltration / breach attempt",
      business_impact: { affected_users: 10000, risk: "CRITICAL" }
    };
  }
}

function getMockRemediation(incident_type: string) {
  const type = (incident_type || "").toUpperCase();
  if (type === "CPU_SPIKE") {
    return {
      recommended_option: {
        action: "kubectl scale deployment api-gateway --replicas=3",
        success_probability: 95,
        downtime_estimate: "0m"
      },
      ranked_options: [
        {
          action: "kubectl scale deployment api-gateway --replicas=3",
          success_probability: 95,
          downtime_estimate: "0m"
        },
        {
          action: "kubectl rollout restart deployment api-gateway",
          success_probability: 70,
          downtime_estimate: "1m"
        }
      ],
      rollback_plan: "kubectl scale deployment api-gateway --replicas=1"
    };
  } else if (type === "DISK_FULL") {
    return {
      recommended_option: {
        action: "kubectl exec postgres-primary-5f2c8b7d4 -- df -h",
        success_probability: 90,
        downtime_estimate: "0m"
      },
      ranked_options: [
        {
          action: "kubectl exec postgres-primary-5f2c8b7d4 -- df -h",
          success_probability: 90,
          downtime_estimate: "0m"
        }
      ],
      rollback_plan: "No rollback required for safe diagnostics"
    };
  } else if (type === "UNAUTHORIZED_ACCESS") {
    return {
      recommended_option: {
        action: "kubectl delete pod auth-service-4a2e1b3c8",
        success_probability: 85,
        downtime_estimate: "10s"
      },
      ranked_options: [
        {
          action: "kubectl delete pod auth-service-4a2e1b3c8",
          success_probability: 85,
          downtime_estimate: "10s"
        }
      ],
      rollback_plan: "Pod will auto-recreate via ReplicaSet"
    };
  } else if (type === "PHISHING_ATTACK") {
    return {
      recommended_option: {
        action: "kubectl delete pod identity-provider-9f2c",
        success_probability: 90,
        downtime_estimate: "10s"
      },
      ranked_options: [
        {
          action: "kubectl delete pod identity-provider-9f2c",
          success_probability: 90,
          downtime_estimate: "10s"
        }
      ],
      rollback_plan: "Pod auto-recreates via ReplicaSet"
    };
  } else if (type === "DDOS_ATTACK") {
    return {
      recommended_option: {
        action: "kubectl scale deployment ingress-gateway-abc1 --replicas=4",
        success_probability: 93,
        downtime_estimate: "0m"
      },
      ranked_options: [
        {
          action: "kubectl scale deployment ingress-gateway-abc1 --replicas=4",
          success_probability: 93,
          downtime_estimate: "0m"
        }
      ],
      rollback_plan: "kubectl scale deployment ingress-gateway-abc1 --replicas=1"
    };
  } else {
    return {
      recommended_option: {
        action: "kubectl delete pod database-primary-z5r2",
        success_probability: 88,
        downtime_estimate: "15s"
      },
      ranked_options: [
        {
          action: "kubectl delete pod database-primary-z5r2",
          success_probability: 88,
          downtime_estimate: "15s"
        }
      ],
      rollback_plan: "Pod auto-recreates via ReplicaSet"
    };
  }
}

// Step 1: Root Cause Analysis
const analyze_root_cause = createStep({
  id: "analyze_root_cause",
  description: "Run RCA agent to determine root cause",
  execute: async ({ getInitData }) => {
    const incident = getInitData() as IncidentData;
    const prompt = `Analyze this incident and determine root cause:
Type: ${incident.incident_type}
Data: ${JSON.stringify(incident.alert_data)}
Metrics available: ${Object.keys(incident.metrics || {}).join(", ")}
Logs entries: ${(incident.logs || []).length} entries`;

    try {
      const result = await rcaAgent.generate(prompt);
      const rca_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return rca_result;
    } catch (err) {
      console.warn("RCA Agent failed, running simulation fallback:", err);
      return getMockRca(incident.incident_type);
    }
  }
});

// Step 2: Threat Intelligence Enrichment
const enrich_threat_intel = createStep({
  id: "enrich_threat_intel",
  description: "Run threat intel agent to enrich incident data",
  execute: async ({ getInitData, getStepResult }) => {
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    const incident = getInitData() as IncidentData;
    const prompt = `Enrich this incident with threat intelligence:
Incident Type: ${incident.incident_type}
Root Cause: ${JSON.stringify(rca_result)}
Look for IOCs (IPs, domains, hashes, URLs, emails) and check threat databases`;

    try {
      const result = await threatIntelAgent.generate(prompt);
      const threat_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return threat_result;
    } catch (err) {
      console.warn("Threat Intel Agent failed, running simulation fallback:", err);
      return getMockThreat(incident.incident_type);
    }
  }
});

// Step 3: Prioritization
const prioritize_incident = createStep({
  id: "prioritize_incident",
  description: "Run prioritization agent to assign SLA",
  execute: async ({ getInitData, getStepResult }) => {
    const incident = getInitData() as IncidentData;
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    const threat_result = getStepResult("enrich_threat_intel") as Record<string, any>;

    const prompt = `Prioritize this incident:
Type: ${incident.incident_type}
RCA Confidence: ${rca_result?.confidence || 0}%
Threat Level: ${threat_result?.threat_level || "unknown"}
Affected Services: ${JSON.stringify(incident.alert_data)}`;

    try {
      const result = await prioritizationAgent.generate(prompt);
      const priority_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return priority_result;
    } catch (err) {
      console.warn("Prioritization Agent failed, running simulation fallback:", err);
      return getMockPriority(incident.incident_type);
    }
  }
});

// Step 4: Remediation Planning
const plan_remediation = createStep({
  id: "plan_remediation",
  description: "Run remediation agent to suggest actions",
  execute: async ({ getInitData, getStepResult }) => {
    const incident = getInitData() as IncidentData;
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    const priority_result = getStepResult("prioritize_incident") as Record<string, any>;
    const threat_result = getStepResult("enrich_threat_intel") as Record<string, any>;

    const prompt = `Plan remediation for this incident:
Root Cause: ${JSON.stringify(rca_result)}
Priority: ${priority_result?.priority_level || "unknown"}
Threat Level: ${threat_result?.threat_level || "unknown"}
Business Impact: ${JSON.stringify(priority_result?.business_impact || {})}

Suggest multiple remediation options ranked by safety and effectiveness.`;

    try {
      const result = await remediationAgent.generate(prompt);
      const remediation_options = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
      return remediation_options;
    } catch (err) {
      console.warn("Remediation Agent failed, running simulation fallback:", err);
      return getMockRemediation(incident.incident_type);
    }
  }
});

// Step 5: Return workflow result
const workflow_complete = createStep({
  id: "workflow_complete",
  description: "Workflow execution complete",
  execute: async ({ getInitData, getStepResult }) => {
    const incident = getInitData() as IncidentData;
    const rca_result = getStepResult("analyze_root_cause");
    const threat_result = getStepResult("enrich_threat_intel");
    const priority_result = getStepResult("prioritize_incident");
    const remediation_options = getStepResult("plan_remediation");

    return {
      status: "completed",
      incident_id: incident.incident_id,
      rca: rca_result,
      threats: threat_result,
      priority: priority_result,
      remediation: remediation_options
    };
  }
});

// Chain steps sequentially and commit
incidentResponseWorkflow
  .then(analyze_root_cause)
  .then(enrich_threat_intel)
  .then(prioritize_incident)
  .then(plan_remediation)
  .then(workflow_complete)
  .commit();
