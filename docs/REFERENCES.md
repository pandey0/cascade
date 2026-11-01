# References

Read in full this session: [1], plus the repo [2]. Abstract-level only: [3]-[5]. Recalled or taken from [1]'s reference list (verify arXiv IDs before citing): the rest.

1. A. Rida. *TRACER: Trace-Based Adaptive Cost-Efficient Routing for LLM Classification.* arXiv:2604.14531v1, 16 Apr 2026. https://arxiv.org/abs/2604.14531 (PDF: https://arxiv.org/pdf/2604.14531). Local copy: `papers/rida2026-tracer-arxiv-2604.14531.pdf` (gitignored; arXiv-hosted, cite and link rather than redistribute).
   ```bibtex
   @article{rida2026tracer,
     title   = {TRACER: Trace-Based Adaptive Cost-Efficient Routing for LLM Classification},
     author  = {Rida, Adam},
     journal = {arXiv preprint arXiv:2604.14531},
     year    = {2026}
   }
   ```
2. TRACER code: https://github.com/adrida/tracer (MIT; PyPI `tracer-llm`). Record the commit you test against.
3. Gupta et al. *Language Model Cascades: Token-level uncertainty and beyond.* ICLR 2024. arXiv:2404.10136.
4. Abbasi Yadkori et al. *Mitigating LLM Hallucinations via Conformal Abstention.* arXiv:2405.01563.
5. *UniCR* (calibration + conformal risk-controlled refusal), arXiv:2509.01455; *RouteLMT*, arXiv:2604.22520; learned abstention thresholds, arXiv:2502.06884; CanDist, arXiv:2506.03857 (seen in search; not read).

From TRACER's reference list (IDs as printed there): Madras et al. 2018 (learning to defer, NeurIPS); Mozannar and Sontag 2020 (ICML); Mozannar et al. 2023 (AISTATS); Narasimhan et al. 2022 (NeurIPS); Dohan et al. *Language model cascades* arXiv:2207.10342; Chen, Zaharia, Zou *FrugalGPT* (ICML 2023; arXiv:2305.05176); Ding et al. *Hybrid LLM* (ICLR 2024); Ong et al. *RouteLLM* arXiv:2406.18665; Madaan et al. *AutoMix* arXiv:2310.12963; Angelopoulos and Bates *A gentle introduction to conformal prediction* arXiv:2107.07511; Hsieh et al. *Distilling step-by-step* (Findings of ACL 2023); Casanueva et al. 2020 (Banking77); Larson et al. 2019 (CLINC150); Williams et al. 2018 (MNLI); Chung et al. 2019 (Slice Finder); Wachter et al. 2017; Rida et al. 2023 (DeltaXplainer).
Also to read (recalled, verify): Angelopoulos et al. *Conformal Risk Control*; *Learn then Test*; Bates et al. *Distribution-free, risk-controlling prediction sets*; Geifman and El-Yaniv *Selective classification for deep neural networks*; Guo et al. *On calibration of modern neural networks*.

Jev / System 1: https://typesafe.ai ; SDKs https://github.com/typesafe-ai/typesafe-sdk-python ; open reproduction of the interface pattern: https://github.com/TheoLeeCJ/SemIf-OpenJev . See `notes/jev-and-open-alternatives.md`.
