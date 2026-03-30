# HireLogic Scripts

## Add a New Candidate

```bash
python scripts/add_candidate.py \
  --job-id 1 \
  --anon-id "candidate-uuid-006" \
  --years-exp 7 \
  --skills "Python,PyTorch,Kubernetes,MLflow" \
  --summary "ML engineer with 7 years building production recommendation systems. Led team of 4 engineers at a Series B startup. Published 1 paper on efficient transformer inference." \
  --status screening
```

## What It Does

1. Creates resume documents in `documents/`
2. Inserts candidate + application in PostgreSQL
3. Next ranking query includes the new candidate

## Remove a Candidate (for demo reset)

```bash
python scripts/remove_candidate.py \
  --anon-id "candidate-uuid-006"
```
