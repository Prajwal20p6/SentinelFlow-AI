import { describe, it } from "node:test";
import assert from "node:assert";
import { getMockRca, getMockThreat, getMockPriority, getMockRemediation } from "./incident-response.workflow";

describe("Mastra Workflow Simulation Fallbacks", () => {
  it("getMockRca sets is_simulated to true and includes simulation_reason", () => {
    const mockReason = "API Key Invalid or Timeout Error";
    const res = getMockRca("CPU_SPIKE", "INC-123", mockReason);
    assert.strictEqual(res.is_simulated, true);
    assert.strictEqual(res.simulation_reason, mockReason);
    assert.ok(res.confidence > 0);
  });

  it("getMockThreat sets is_simulated to true and includes simulation_reason", () => {
    const mockReason = "Rate Limit 429 Exceeded";
    const res = getMockThreat("UNAUTHORIZED_ACCESS", "INC-124", mockReason);
    assert.strictEqual(res.is_simulated, true);
    assert.strictEqual(res.simulation_reason, mockReason);
    assert.strictEqual(res.threat_level, "critical");
  });

  it("getMockPriority sets is_simulated to true and includes simulation_reason", () => {
    const mockReason = "LLM provider unreachable";
    const res = getMockPriority("DISK_FULL", "INC-125", mockReason);
    assert.strictEqual(res.is_simulated, true);
    assert.strictEqual(res.simulation_reason, mockReason);
    assert.strictEqual(res.priority_level, "P2");
  });

  it("getMockRemediation sets is_simulated to true and includes simulation_reason", () => {
    const mockReason = "Failed to parse LLM JSON output";
    const res = getMockRemediation("ERROR_RATE_SPIKE", "INC-126", mockReason);
    assert.strictEqual(res.is_simulated, true);
    assert.strictEqual(res.simulation_reason, mockReason);
    assert.ok(res.recommended_option);
  });
});
