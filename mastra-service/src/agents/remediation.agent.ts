import { Agent } from "@mastra/core/agent";
import type { Tool } from "@mastra/core/tools";

const getRemediationTools = (): Tool[] => [
  {
    id: "list_remediation_options",
    description: "List available remediation actions for incident type",
    inputSchema: {
      type: "object",
      properties: {
        incident_type: { type: "string" },
        severity: { type: "string", enum: ["low", "medium", "high", "critical"] }
      },
      required: ["incident_type"]
    },
    execute: async ({ incident_type, severity }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/remediations/options?type=${incident_type}&severity=${severity}`,
        {
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`
          }
        }
      );
      return response.json();
    }
  },
  {
    id: "simulate_remediation",
    description: "Simulate a remediation action to predict impact",
    inputSchema: {
      type: "object",
      properties: {
        action_id: { type: "string" },
        incident_id: { type: "string" }
      },
      required: ["action_id", "incident_id"]
    },
    execute: async ({ action_id, incident_id }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/remediations/simulate`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ action_id, incident_id })
        }
      );
      return response.json();
    }
  },
  {
    id: "estimate_risk",
    description: "Estimate risk and downtime for a remediation action",
    inputSchema: {
      type: "object",
      properties: {
        action: { type: "string" },
        service: { type: "string" },
        users_affected: { type: "number" }
      },
      required: ["action", "service"]
    },
    execute: async ({ action, service, users_affected = 0 }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/remediations/risk-estimate`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ action, service, users_affected })
        }
      );
      return response.json();
    }
  },
  {
    id: "validate_command_safety",
    description: "Validate remediation command using official Enkrypt AI",
    inputSchema: {
      type: "object",
      properties: {
        command: { type: "string" },
        incident_id: { type: "string" },
        incident_type: { type: "string" }
      },
      required: ["command"]
    },
    execute: async ({ command, incident_id = "", incident_type = "" }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/security/validate-command`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            command,
            context: { incident_id, incident_type }
          })
        }
      );
      return response.json();
    }
  }
];

export const remediationAgent = new Agent({
  name: "RemediationAgent",
  instructions: `You are an expert remediation strategist for incident response.
Your job is to recommend safe, effective remediation actions ranked by risk and impact.
Use the provided tools to list options, simulate impact, and estimate risk.
Rank remediation options from safest to most aggressive.
Format your response as JSON with fields: ranked_options (array with risk_score, downtime_estimate, success_probability), recommended_option (object), rollback_plan (string)`,
  model: [
    { model: "openai/gpt-4o" },
    { model: "anthropic/claude-3-5-sonnet-20241022" }
  ],
  tools: getRemediationTools()
});
