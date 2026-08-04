# Survey Update Audit

Last audited: August 4, 2026

The survey is available at [https://doi.org/10.13140/RG.2.2.21157.87528](https://doi.org/10.13140/RG.2.2.21157.87528).

## Which PDF is newer?

Despite its filename, `paper_old.pdf` is the newer draft. Its PDF metadata reports August 4, 2026, while `paper.pdf` reports July 13, 2026. The August draft also contains the expanded author list and the additional group publications. This audit therefore describes the August draft as the revised draft and the July PDF as the baseline.

## Revision summary

| Item | July baseline (`paper.pdf`) | August revised draft (`paper_old.pdf`) |
|:--|:--|:--|
| Authors | Zikai Song and Xiajie Li | Adds Yunyao Zhang, Xinglang Zhang, Wei Yang, and Junqing Yu |
| Introduction | Challenges and contributions | Adds explicit Background and Analysis of Existing Surveys subsections |
| Section 2 | Background and Scope; Technical Paradigms | Renamed Scope and Overview; adds Positioning SIM and Organization and Taxonomy |
| Main-text words before references | 10,784 | 10,465 |
| References | 290 | 303 |
| Zikai Song references | 1 | 22 |
| Front matter | ACM reference format, rights notice, and manuscript status are present | These ACM front-matter elements are absent; the layout reads more like a public preprint |

The revised draft adds 21 Zikai Song co-authored references and removes eight foundational references: Bonabeau on agent-based modeling, GPT-3, BERT, RAG, Transformer, chain-of-thought prompting, ReAct, and a GNN review.

## Recommended Zotero/database actions

`Add` means the paper has a direct and defensible fit with the current taxonomy. `Borderline` means it should be added only if the repository intentionally includes general enabling methods. `Do not add` means the paper does not study social intelligence or social-media analysis closely enough for the current collection.

| Revised ref. | Paper and authoritative link | Citation in revised draft | Recommended repository category | Action |
|:--:|:--|:--|:--|:--|
| 49 | [MA-VLAD: A Fine-Grained Local Feature Aggregation Scheme for Action Recognition](https://doi.org/10.1007/s00530-024-01341-9) | p. 9, §4.1.1 Event Extraction; bibliography p. 24 | No defensible current category; it is action recognition rather than social event extraction | Do not add |
| 75 | [SF2T: Self-Supervised Fragment Finetuning of Video-LLMs for Fine-Grained Understanding](https://openaccess.thecvf.com/content/CVPR2025/html/Hu_SF2T_Self-supervised_Fragment_Finetuning_of_Video-LLMs_for_Fine-Grained_Understanding_CVPR_2025_paper.html) | p. 10, §4.1.3 Meme and Multimodal Understanding; bibliography p. 25 | Meme and Multimodal Understanding, but only with an explicit social-media rationale | Borderline |
| 111 | [Large Language Model as Token Compressor and Decompressor](https://arxiv.org/abs/2603.25340) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 27 | Other (general LLM infrastructure) | Borderline |
| 112 | [LoRA-Mixer: Coordinate Modular LoRA Experts Through Serial Attention Routing](https://arxiv.org/abs/2507.00029) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 27 | Other (general LLM adaptation) | Borderline |
| 113 | [Coupled Mamba: Enhanced Multimodal Fusion with Coupled State Space Model](https://papers.nips.cc/paper_files/paper/2024/hash/6e09c213ac18d6375704a4f3ea75c4f8-Abstract-Conference.html) | p. 7, §3.1.4 Sentiment Analysis; bibliography p. 27 | Sentiment Analysis; optionally Meme and Multimodal Understanding | Add |
| 129 | [GateMOT: Q-Gated Attention for Dense Object Tracking](https://arxiv.org/abs/2604.26353) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 28 | No defensible current category; it is multi-object tracking | Do not add |
| 192 | [Temporal Coherent Object Flow for Multi-Object Tracking](https://ojs.aaai.org/index.php/AAAI/article/view/32749) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 30 | No defensible current category; it is multi-object tracking | Do not add |
| 193 | [Compact Transformer Tracker with Correlative Masked Modeling](https://ojs.aaai.org/index.php/AAAI/article/view/25327) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 30 | No defensible current category; it is visual object tracking | Do not add |
| 194 | [Autogenic Language Embedding for Coherent Point Tracking](https://doi.org/10.1145/3664647.3681104) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 30 | No defensible current category; it is point tracking | Do not add |
| 195 | [Transformer Tracking with Cyclic Shifting Window Attention](https://openaccess.thecvf.com/content/CVPR2022/html/Song_Transformer_Tracking_With_Cyclic_Shifting_Window_Attention_CVPR_2022_paper.html) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 30 | No defensible current category; it is visual object tracking | Do not add |
| 196 | [Hypergraph-State Collaborative Reasoning for Multi-Object Tracking](https://openaccess.thecvf.com/content/CVPR2026/html/Song_Hypergraph-State_Collaborative_Reasoning_for_Multi-Object_Tracking_CVPR_2026_paper.html) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 30 | No defensible current category; it is multi-object tracking | Do not add |
| 220 | [Seeing Further and Wider: Joint Spatio-Temporal Enlargement for Micro-Video Popularity Prediction](https://arxiv.org/abs/2604.20311) | p. 10, §4.2.1 Social Popularity Prediction; bibliography p. 31 | Social Popularity Prediction | Add |
| 236 | [HotComment: A Benchmark for Evaluating Popularity of Online Comments](https://arxiv.org/abs/2604.25614) | p. 11, §5.1.1 Comment Generation; bibliography p. 32 | Comment Generation and Social Popularity Prediction | Add |
| 261 | [OmniTrend: Content-Context Modeling for Scalable Social Popularity Prediction](https://arxiv.org/abs/2604.26252) | p. 10, §4.2.1 Social Popularity Prediction; bibliography p. 33 | Social Popularity Prediction | Add |
| 262 | [MVP: Winning Solution to SMP Challenge 2025 Video Track](https://doi.org/10.1145/3746027.3763761) | p. 10, §4.2.1 Social Popularity Prediction; bibliography p. 33 | Social Popularity Prediction | Already present; do not add another row |
| 269 | [CurEvo: Curriculum-Guided Self-Evolution for Video Understanding](https://arxiv.org/abs/2604.26707) | p. 10, §4.1.3 Meme and Multimodal Understanding; bibliography p. 33 | Meme and Multimodal Understanding, but only with an explicit social-media rationale | Borderline |
| 285 | [Logical Phase Transitions: Understanding Collapse in LLM Logical Reasoning](https://aclanthology.org/2026.acl-long.858/) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 34 | Other (general LLM reasoning) | Borderline |
| 286 | [Coupling Macro Dynamics and Micro States for Long-Horizon Social Simulation](https://arxiv.org/abs/2604.05516) | p. 16, §6.3.1 Macro Social Alignment; bibliography p. 34 | Macro Social Alignment; optionally Macro Social Phenomena Analysis | Add |
| 288 | [GA-S3: Comprehensive Social Network Simulation with Group Agents](https://aclanthology.org/2025.findings-acl.468/) | pp. 14, 16, and 20: Table 3, §6.3.1, and Table 4; bibliography p. 34 | LLM-Empowered Agent-Based Modeling, Macro Social Alignment, and Sociology and Social Media | Already present; enrich categories instead of adding another row |
| 290 | [IntervenSim: Intervention-Aware Social Network Simulation for Opinion Dynamics](https://arxiv.org/abs/2604.06600) | p. 17, §6.3.2 Macro Social Phenomena Analysis; bibliography p. 34 | Macro Social Phenomena Analysis and Sociology and Social Media | Add |
| 291 | [Semantic-Aware Logical Reasoning via a Semiotic Framework](https://aclanthology.org/2026.acl-long.835/) | p. 5, §2.2 Positioning Social Intelligence Modeling; bibliography p. 34 | Other; possibly Discourse and Pragmatic Analysis only if the scope explicitly includes non-social logical semantics | Borderline |
| 299 | [Video Anomaly Detection with Motion and Appearance Guided Patch Diffusion Model](https://ojs.aaai.org/index.php/AAAI/article/view/33169) | p. 10, §4.1.3 Meme and Multimodal Understanding; bibliography p. 35 | No defensible current category; the task is surveillance video anomaly detection | Do not add |

## Database warnings

- `GA-S3` and `MVP` already occur in both databases. The current working database also contains duplicate rows for each title, so importing them again would make the duplication worse.
- Add or merge the seven high-fit records first: Coupled Mamba, Seeing Further and Wider, HotComment, OmniTrend, Coupling Macro Dynamics and Micro States, GA-S3 category enrichment, and IntervenSim.
- Treat all generic tracking, action-recognition, and surveillance-anomaly papers as out of scope unless the survey taxonomy is deliberately expanded and the manuscript explains that scope change.

## Editorial assessment

The August revision is stronger in structure: it gives the field definition more context, adds a comparison with existing surveys, makes the taxonomy easier to motivate, and correctly expands the author list. Its social-popularity and social-simulation additions also improve coverage.

The revision is weaker in citation discipline. Several new citations do not support the claims attached to them: MA-VLAD is described as event-dynamics modeling, tracking papers are used to support broad representation-learning and Transformer claims, and a logical-reasoning paper is cited as evidence of intelligent-agent development. Replacing eight canonical foundation references with these group papers further increases the appearance of self-citation without improving support for the corresponding claims. The best revision would keep the structural rewrite, restore the foundational references, retain the directly relevant social-media and simulation papers, and remove or relocate the unrelated computer-vision citations.
