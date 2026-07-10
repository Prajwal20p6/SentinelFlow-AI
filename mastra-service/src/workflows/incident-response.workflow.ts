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

    const result = await rcaAgent.generate(prompt);
    const rca_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
    return rca_result;
  }
});

// Step 2: Threat Intelligence Enrichment
const enrich_threat_intel = createStep({
  id: "enrich_threat_intel",
  description: "Run threat intel agent to enrich incident data",
  execute: async ({ getInitData, getStepResult }) => {
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    if (!rca_result) return { status: "skipped", reason: "No RCA result" };

    const incident = getInitData() as IncidentData;
    const prompt = `Enrich this incident with threat intelligence:
Incident Type: ${incident.incident_type}
Root Cause: ${JSON.stringify(rca_result)}
Look for IOCs (IPs, domains, hashes, URLs, emails) and check threat databases`;

    const result = await threatIntelAgent.generate(prompt);
    const threat_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
    return threat_result;
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

    const result = await prioritizationAgent.generate(prompt);
    const priority_result = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
    return priority_result;
  }
});

// Step 4: Remediation Planning
const plan_remediation = createStep({
  id: "plan_remediation",
  description: "Run remediation agent to suggest actions",
  execute: async ({ getStepResult }) => {
    const rca_result = getStepResult("analyze_root_cause") as Record<string, any>;
    if (!rca_result) return { status: "skipped", reason: "No RCA result" };

    const priority_result = getStepResult("prioritize_incident") as Record<string, any>;
    const threat_result = getStepResult("enrich_threat_intel") as Record<string, any>;

    const prompt = `Plan remediation for this incident:
Root Cause: ${JSON.stringify(rca_result)}
Priority: ${priority_result?.priority_level || "unknown"}
Threat Level: ${threat_result?.threat_level || "unknown"}
Business Impact: ${JSON.stringify(priority_result?.business_impact || {})}

Suggest multiple remediation options ranked by safety and effectiveness.`;

    const result = await remediationAgent.generate(prompt);
    const remediation_options = typeof result.text === "string" ? JSON.parse(result.text) : result.text;
    return remediation_options;
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
