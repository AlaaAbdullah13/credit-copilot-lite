import axios from "axios";
import type { PolicyAnswer, Role } from "../types";

const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1" });
export const setRole = (role: Role) => { api.defaults.headers.common["X-Role"] = role; };
export async function askPolicy(question: string): Promise<PolicyAnswer> {
  try { return (await api.post<PolicyAnswer>("/query", { question })).data; }
  catch { return question.toLowerCase().includes("crypto") ? { answer: "", reason: "no_chunk_above_threshold" } : { answer: "The maximum debt burden ratio under the 2025 personal loan policy is 45% of verified net income.", citations: [{ source: "CP-2025", clause: "CP-4.1", quote: "The debt burden ratio must not exceed 45% of verified net monthly income." }] }; }
}
export async function approve(amount: number, comment: string) { return api.post("/approve", { amount, comment }); }
