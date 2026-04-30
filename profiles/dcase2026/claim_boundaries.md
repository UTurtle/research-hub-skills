# DCASE2026 Claim Boundaries

- `main6 noise-aware residual` is deployable only for a single global setting.
- `surface-aware selector` is diagnostic or oracle unless its selection rule is
  fixed without dev-label leakage.
- `main24 learnable branch` is learned representation plus fixed density
  backend, not a full end-to-end anomaly scorer.
- `main22/main23 synthetic branch` changes normal source or source law and
  must be revalidated before final source-replacement claims.
