# =============================================
# VAULT LIFECYCLE PROTOCOL
# =============================================
# Defines the complete lifecycle of every artifact in the Vault, from birth to retirement.

# ─── Artifact Lifecycle Stages ──────────────
lifecycle_stages:
  - name: "created"
    description: "Artifact created and validated"
    required_actions: ["documentation", "verification"]

  - name: "in_use"
    description: "Artifact actively referenced in code or documentation"
    required_actions: ["usage_tracking", "performance_metrics"]

  - name: "declined"
    description: "Artifact is outdated but still referenced for comparison"
    required_actions: ["deprecation_notice", "migration_guide"]

  - name: "retired"
    description: "Artifact fully retired, preserved for reference only"
    required_actions: ["retirement_summary", "replacement_path"]

  - name: "archived"
    description: "Artifact moved to long-term storage, not actively maintained"
    required_actions: ["archive_location", "access_level"]

# ─── Quick Summary Template for Life Cycle ──
lifecycle_summary_template: |
  ## Component Lifecycle Summary

  ### Overview
  - **Component**: [name]
  - **Created**: [date] by [author]
  - **Retired**: [date or N/A]
  - **Status**: [active | declined | retired | archived]

  ### What It Did
  - Purpose: [one sentence]
  - Scope: [what it covered]

  ### Why It Was Retired/Changed
  - Primary Reason: [why it changed]
  - Technical Debt: [what was wrong with it]
  - Performance Impact: [before/after metrics if applicable]

  ### Replacement
  - New Component: [path/name]
  - Migration Steps:
    1. [step 1]
    2. [step 2]

  ### Verification
  - [ ] All references updated
  - [ ] Tests updated/removed
  - [ ] Documentation updated
