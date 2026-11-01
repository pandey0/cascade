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

## Added 2026-11-01 (checked against arXiv abstract pages unless noted)
Geifman & El-Yaniv, arXiv:1705.08500; Angelopoulos et al. (LTT), arXiv:2110.01052; Waudby-Smith & Ramdas, arXiv:2010.09686 (formulas read from the paper); Podkopaev & Ramdas, arXiv:2110.06177; Dou, Lian, Li (Conformal Cascade), arXiv:2607.25018; Jia et al. (BalanceRAG), arXiv:2605.20084; Gupta et al., arXiv:2404.10136 and Abbasi Yadkori et al., arXiv:2405.01563 (authors/dates verified). See `notes/literature-check.md`.

## Key references with links (moved from the README)
Closest prior work and the methods this project builds on (details and overlap assessment in `docs/notes/literature-check.md`; full bibliography in `paper/references.bib`):
- A. Rida, *TRACER: Trace-Based Adaptive Cost-Efficient Routing for LLM Classification*, [arXiv:2604.14531](https://arxiv.org/abs/2604.14531); code [github.com/adrida/tracer](https://github.com/adrida/tracer) (MIT).
- Y. Geifman, R. El-Yaniv, *Selective Classification for Deep Neural Networks*, NeurIPS 2017, [arXiv:1705.08500](https://arxiv.org/abs/1705.08500) (threshold selection with a binomial bound and Bonferroni correction: the origin of certified selection).
- A. N. Angelopoulos, S. Bates, E. J. Candes, M. I. Jordan, L. Lei, *Learn then Test*, [arXiv:2110.01052](https://arxiv.org/abs/2110.01052).
- I. Waudby-Smith, A. Ramdas, *Estimating means of bounded random variables by betting*, [arXiv:2010.09686](https://arxiv.org/abs/2010.09686) (the confidence sequence used by the drift alarm); A. Podkopaev, A. Ramdas, *Tracking the risk of a deployed model and detecting harmful distribution shifts*, [arXiv:2110.06177](https://arxiv.org/abs/2110.06177).
- Y. Dou, S. Lian, S. Li, *Conformal Cascade*, [arXiv:2607.25018](https://arxiv.org/abs/2607.25018); Z. Jia et al., *BalanceRAG*, [arXiv:2605.20084](https://arxiv.org/abs/2605.20084); N. Gupta et al., *Language Model Cascades: Token-level uncertainty and beyond*, [arXiv:2404.10136](https://arxiv.org/abs/2404.10136); Y. Abbasi Yadkori et al., *Mitigating LLM Hallucinations via Conformal Abstention*, [arXiv:2405.01563](https://arxiv.org/abs/2405.01563).
- Data: Banking77 (Casanueva et al. 2020, CC-BY-4.0) and CLINC150 (Larson et al. 2019, CC-BY-3.0), licences as stated on their Hugging Face cards.
- Standards: OWASP ASVS 5.0.0 (`docs/security.md`), Google SRE Workbook, "Alerting on SLOs" (`docs/slo.md`).
