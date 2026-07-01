# Corrobo

## What this is
A hallucination/factuality checker: user submits a source document + an AI-generated
summary of it. The tool uses RAG to retrieve relevant source chunks per claim, then an
LLM judges whether each claim is supported. Long-term: shaped as a commercializable
SaaS (multi-user, auth), not just a single-user demo.

Origin: extends my MSc thesis work on MedHAL (hallucination detection in clinical
language models, fine-tuned BioClinicalBERT) into a live tool using modern LLM APIs
and RAG, instead of a fixed classifier on a fixed dataset.

## Stack
- Backend: FastAPI (Python)
- DB: PostgreSQL
- Vector store: ChromaDB
- Embeddings: sentence-transformers (HuggingFace)
- LLM: Anthropic API (Claude)
- Auth: basic email/password, user-scoped data (no OAuth/SSO for now)
- Deployment target: Docker + docker-compose, AWS EC2, GitHub Actions CI
- Billing: Stripe — stretch goal only, not required for MVP

## Timeline (part-time, alongside thesis + daily LeetCode)
- Week 1: FastAPI skeleton, first LLM API call, PostgreSQL storage
- Week 2: RAG pipeline — chunking, embeddings, ChromaDB, retrieval before LLM call
- Week 3: PyTest tests, Dockerfile, docker-compose, GitHub Actions CI
- Week 4: Deploy to AWS EC2, live at a real URL
- Week 5: Auth (email/password), scope data to user_id, minimal frontend
- Week 6-7: Polish, README, architecture diagram, spoken project explanation;
  Stripe stub if time allows

## Current phase
Week 1 — basic API skeleton, first LLM call, PostgreSQL storage. No RAG, no auth yet.

## How I want you to work with me
I've always used AI for coding and want to actually learn properly here — not just
ship a deliverable. But I also have a fixed timeline (thesis + job applications
running in parallel), so effort should be spent where it's actually differentiating
in interviews, not applied uniformly everywhere. Split into two tiers:

### Tier 1 — I write it, you review (do NOT write implementation code for me)
Applies to: SQL queries, RAG pipeline design, chunking strategy, embeddings,
ChromaDB retrieval logic, prompt design for the LLM judgment step.
- Explain the concept, show a minimal standalone example (not in my actual files),
  then let me write my own version in the project.
- After I write something, review it — point out what's wrong, inefficient, or
  not idiomatic. Point, don't fix, unless I'm stuck and ask you to.
- This is the part interviewers will actually probe deeply, so depth here matters
  more than speed.

### Tier 2 — you can write it, but explain clearly and check I understand
Applies to: Docker/docker-compose, GitHub Actions CI, AWS EC2 setup/deployment,
auth boilerplate (login, session/JWT handling).
- Fine to write this directly to save time.
- Before or alongside writing it, explain what each piece does and why it's
  configured that way — enough that I could re-explain it in an interview.
- Occasionally ask me to explain a piece back in my own words, don't just assume
  it landed.

### General
- Exception to both tiers: FastAPI, PyTorch, HuggingFace, general Python — I know
  these well, move fast, no need to over-explain.
- If I explicitly say "just write it" or "just build X," override tier rules and build it.
- When I'm debugging Tier 1 code, ask guiding questions first rather than
  immediately diagnosing the fix. For Tier 2, fine to just diagnose and fix.
- If there are two reasonable ways to do something, tell me the tradeoff instead
  of silently picking one.

## Conventions
- Keep functions small and testable — PyTest coverage matters from Week 3 on
- No premature auth/billing complexity — email/password only, Stripe is a stretch goal
- Prioritize code I can explain confidently in an interview over code that's merely working

## Not yet built
RAG pipeline, auth, tests, Docker, CI, deployment