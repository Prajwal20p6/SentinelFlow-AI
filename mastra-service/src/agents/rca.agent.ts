import { Agent } from "@mastra/core/agent";
import type { Tool } from "@mastra/core/tools";

const getRCATools = (): Tool[] => [
  {
    id: "get_metrics",
    description: "Fetch metrics for incident analysis",
    inputSchema: {
      type: "object",
      properties: {
        service_name: { type: "string" },
        time_range: { type: "string" }
      },
      required: ["service_name"]
    },
    execute: async ({ service_name, time_range = "1h" }) => {
      // Call Python backend to get metrics
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/services/${service_name}/metrics?range=${time_range}`,
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
    id: "get_logs",
    description: "Fetch logs for incident analysis",
    inputSchema: {
      type: "object",
      properties: {
        service_name: { type: "string" },
        limit: { type: "number" }
      },
      required: ["service_name"]
    },
    execute: async ({ service_name, limit = 100 }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/services/${service_name}/logs?limit=${limit}`,
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
    id: "find_similar_incidents",
    description: "Find similar incidents in history",
    inputSchema: {
      type: "object",
      properties: {
        pattern: { type: "string" },
        limit: { type: "number" }
      },
      required: ["pattern"]
    },
    execute: async ({ pattern, limit = 5 }) => {
      const response = await fetch(
        `${process.env.PYTHON_BACKEND_URL}/api/v1/incidents/similar?pattern=${pattern}&limit=${limit}`,
        {
          headers: {
            "Authorization": `Bearer ${process.env.PYTHON_BACKEND_API_KEY}`
          }
        }
      );
      return response.json();
    }
  }
];

export const rcaAgent = new Agent({
  name: "RootCauseAnalysisAgent",
  instructions: `You are an expert incident analyst specialized in root cause analysis.
Your job is to analyze metrics, logs, and incident history to identify the root cause of incidents.
Use the provided tools to gather data about the service and metrics.
Provide a structured RCA with confidence scores and supporting evidence.
Format your response as JSON with fields: root_cause, confidence (0-100), evidence (array), similar_incidents (array)`,
  model: [
    { model: "openai/gpt-4o" },
    { model: "anthropic/claude-3-5-sonnet-20241022" }
  ],
  tools: getRCATools()
});
