import dotenv from "dotenv";
dotenv.config();

/**
 * Centralized secret and environment value getter for Mastra Service.
 * Supports local environment variables (default) and opt-in cloud secret providers.
 */
export function getSecret(key: string, defaultValue: string = ""): string {
  const provider = (process.env.SECRETS_PROVIDER || "env").toLowerCase();

  if (provider === "aws") {
    return process.env[key] || process.env[key.toUpperCase()] || defaultValue;
  }

  return process.env[key] || defaultValue;
}
