# Compute plan: local machine and Google Colab

## Your machine (checked)
8 CPU cores, 15 GB RAM, NVIDIA MX330 (about 2 GB VRAM), Python 3.10. Good for: all of Cascade's core library, TF-IDF/embedding+LR students, small sentence-transformer encoders (MiniLM class), the gateway, tests, CI. Not good for: 4B-parameter models on GPU, encoder fine-tuning beyond tiny models, BGE-large embeddings at scale (possible on CPU but slow: measure).

## Is Colab fine? Yes, as an optional GPU box
Reported (third-party sources, conflicting; Google does not publish exact limits): free tier gives a dynamic, non-guaranteed GPU (commonly a T4 with 16 GB), sessions can disconnect, idle timeouts and hard caps exist. Paid tiers give more reliable GPUs. Plan for interruptions.
**Use Colab for:** (1) BGE-large embeddings of a few thousand to tens of thousands of texts; (2) fine-tuning a small encoder for the MNLI-style extension (E5); (3) open-model typed-decision scoring (SemIf-style 4B) for E6; (4) one-off reproductions of TRACER.
**Do not use Colab for:** the gateway/service, CI, anything with secrets pasted into cells, long unattended jobs without checkpointing.
**Rules:** keep all code in this repo and keep notebooks thin (clone/install, run a script, save outputs); store API keys in Colab's Secrets feature rather than cell text (check the current Colab docs for the exact mechanism); write checkpoints and outputs to Drive; record GPU type, library versions and the git commit in every results file; make every script also runnable on CPU for tests; do not upload data whose licence forbids it or any employer/client data.
Starter: `notebooks/colab_quickstart.ipynb` (runs exp0 and prints the runtime environment).

## Budget notes
Teacher labelling cost formula and caching are in `RESEARCH-ROUTE.md` section 4. Embeddings: compute once, cache to disk (`.npy`), share across experiments. Keep an experiment ledger (`results/ledger.csv`: date, commit, hardware, wall time, API spend).
