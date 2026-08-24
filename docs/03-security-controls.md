# Security Controls — Deep Dive: IAM, RBAC, GA

## 1. Identity & Access Management (IAM) — Architecture

### 1.1 Authentication Flow (OIDC/OAuth2)
- User → Auth Gateway → Keycloak/Auth0 → Token Issuance (JWT access + refresh token)
- Session cached in Redis with TTL

### 1.2 MFA / Multi-Factor Authentication
| Method | Implementation | Use Case |
|--------|---------------|----------|
| TOTP | `pyotp` — 6-digit code, 30s period | Default for all users |
| WebAuthn / FIDO2 | `webauthn` Python library — hardware key support | Enterprise users, GA accounts |
| Email OTP | One-time password via email (fallback) | Onboarding, device reset |

---

## 2. Role-Based Access Control (RBAC) — Deep Dive

### RBAC Permission Matrix

| Action | GA | Team Admin | Developer | Read-Only | Service Account | Guest (Trial) |
|--------|----:|-----------:|----------:|---------:|----------------:|--------------:|
| Create Workspace | ✅ | ✅ (own team) | ❌ | ❌ | ✅ (scoped) | ❌ |
| Create Sandbox | ✅ | ✅ | ✅ (own sandbox) | ❌ | ✅ | ⚠️ (limited) |
| Delete Sandbox | ✅ | ✅ (own team) | ✅ (own sandbox) | ❌ | ❌ | ❌ |
| Execute Agentic AI | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (basic only) |
| Modify Network Policy | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| View Observability | ✅ | ✅ (own team) | ✅ | ⚠️ (limited) | ❌ | ❌ |
| Modify RBAC Rules | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Export Audit Log | ✅ | ✅ (own team) | ❌ | ⚠️ (limited) | ❌ | ❌ |

### GA Approval Workflow for Critical Actions
Critical actions require approval: `shutdown_all_sandboxes`, `delete_tenant`, `modify_network_policy`
- GA submits action with justification
- Second GA confirmation required
- Audit trail logged with both initiator and approver IDs

### Audit Log Schema (Immutable PostgreSQL Table)
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID NOT NULL,
    actor_type VARCHAR(20) CHECK (actor_type IN ('user', 'service', 'system')),
    action VARCHAR(50) NOT NULL,          -- e.g., 'sandbox:create', 'ga:shutdown_all'
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID NOT NULL,
    action_payload JSONB DEFAULT '{}',   -- Before/after state diff
    result VARCHAR(20) NOT NULL DEFAULT 'success',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signature BYTEA NOT NULL,            -- HMAC-SHA256 for tamper detection
);

CREATE TRIGGER prevent_audit_log_mutation
BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION prevent_audit_row_change();
```

---

## 3. Network Access Control — Zero-Trust Model

### Egress Policy (Whitelist Approach)
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sandbox-egress-policy
spec:
  podSelector:
    matchLabels:
      app: sandbox-instance
  policyTypes:
    - Egress
  egress:
    # DNS resolution
    - to: [hosts: ["10.96.0.2"]] ports: [{protocol: UDP, port: 53}]
    
    # Package registries
    - to: [hosts: ["pypi.org", "crates.io", "registry.npmjs.com"]] ports: [{protocol: TCP, port: 443}]
    
    # API services
    - to: [hosts: ["api.github.com", "oai.openai.com"]] ports: [{protocol: TCP, port: 443}]
    
    # Ollama server (localhost)
    - to: [hosts: ["127.0.0.1"]] ports: [{protocol: TCP, port: 11434}]
```

### Ingress Policy — API Gateway Only
Only allows traffic FROM platform services TO sandbox instances. Blocks all direct inbound TCP access.
