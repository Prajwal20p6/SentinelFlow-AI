import { Agent } from "@mastra/core/agent";
import type { Tool } from "@mastra/core/tools";

const getPrioritizationTools = (): Tool[] => [
  {
    id: "get_service_criticality",
    description: "Get criticality level of affected service",
    inputSchema: {
      type: "object",
      properties: {
        service_name: { type: "string" }
      },
      required: ["service_name"]
    },
    execute: async ({ service_name }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/services/${service_name}/criticality`,
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
    id: "estimate_business_impact",
    description: "Estimate business impact (cost, users, revenue)",
    inputSchema: {
      type: "object",
      properties: {
        incident_type: { type: "string" },
        affected_services: { type: "array", items: { type: "string" } },
        duration_minutes: { type: "number" }
      },
      required: ["incident_type", "affected_services"]
    },
    execute: async ({ incident_type, affected_services, duration_minutes = 0 }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/incidents/business-impact`,
        {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ incident_type, affected_services, duration_minutes })
        }
      );
      return response.json();
    }
  }
];

export const prioritizationAgent = new Agent({
  name: "IncidentPrioritizationAgent",
  instructions: `You are an expert incident prioritization specialist.
Your job is to prioritize incidents based on business impact, service criticality, and security severity.
Use the provided tools to assess business impact and service criticality.
Assign priority levels (P0, P1, P2, P3, P4) with SLA targets.
Format your response as JSON with fields: priority_level (P0-P4), sla_minutes (number), justification (string), business_impact (object)`,
  model: {
    provider: "OPEN_AI",
    name: "gpt-4",
    toolChoice: "auto"
  },
  tools: getPrioritizationTools()
});
