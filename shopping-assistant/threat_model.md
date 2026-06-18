# STRIDE Threat Model Assessment: Shopping Assistant

## System Boundaries
- **Entry Points:** FastAPI application endpoints (HTTP/REST) and the LLM agent invocation path (CLI/API).
- **Data Storage:** In-memory dictionary (`DISCOUNT_CODES`) for state tracking. No persistent session or database storage is configured.

## STRIDE Evaluation

### 1. Spoofing
**Risk:** **High**
- *Are caller identity boundaries verified before executing sensitive tool logic?*
- No. The `redeem_discount_code` tool directly accepts `user_id` as an unverified string parameter from the LLM. An attacker can supply arbitrary user IDs via prompts to claim discount codes under other users' identities. There is no verification linking the session to the `user_id`.

### 2. Tampering
**Risk:** **High**
- *Can users manipulate data flows, parameters, or underlying state?*
- Yes. The LLM tool parameters are parsed dynamically without strict Pydantic schema validation. Malformed `code` or `user_id` strings could be injected. Furthermore, state is stored purely in-memory, making the entire redemption state volatile and susceptible to reset/tampering if the application restarts.

### 3. Repudiation
**Risk:** **Medium**
- *Are critical transactions securely logged?*
- No. The `redeem_discount_code` function alters business state (redeeming a code) without emitting any explicit audit logs. If a code is redeemed maliciously, there is no audit trail recording the transaction details.

### 4. Information Disclosure
**Risk:** **Critical**
- *Are we risking leakage of PII, internal tokens, or raw stack traces?*
- Yes. The `app/agent.py` file contains a **hardcoded Gemini API key** (`api_key="AIzaSyD-mock-key-value-12345"`). This will be committed to version control and completely compromises the credential. Additionally, the LLM might be vulnerable to prompt injection aimed at tricking it into disclosing the contents of the `DISCOUNT_CODES` dictionary.

### 5. Denial of Service (DoS)
**Risk:** **High**
- *Are there rate limits on expensive database or LLM queries?*
- No rate limits or quotas are enforced. Unauthenticated attackers can spam the endpoints with complex prompts, rapidly consuming the LLM context limits, exhausting API quotas, and causing a financial/resource DoS.

### 6. Elevation of Privilege
**Risk:** **High**
- *Can an unauthenticated user bypass access control to reach privileged tool actions?*
- Yes. There is no application-level authentication middleware restricting access to the agent. Any unauthenticated caller can reach the `redeem_discount_code` logic. There are no privilege checks to ensure only authorized entities can perform administrative actions.
