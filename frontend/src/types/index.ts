export type Role = "loan_officer" | "credit_officer";
export type Status = "Approved" | "Pending" | "Refer" | "Rejected";
export interface Application { id: string; applicant: string; status: Status; income: string; obligations: string; amount: number; tenor: string; bureau: number; dbr: string; }
export interface RuleCheck { label: string; pass: boolean; value: string; clause: string; quote: string; }
export interface PolicyAnswer { answer: string; citations?: { source: string; clause: string; quote: string }[]; reason?: string; }
