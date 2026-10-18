# Submission Materials: Applied Acoustics

## Cover Letter

Dear Editors,

We are pleased to submit our manuscript "Error Propagation in Cascaded
Speech Translation under Acoustic Channel Degradations: A Black-Box Case
Study of Commercial Speech Intelligence APIs" for consideration as a
research paper in Applied Acoustics.

Speech recognition and translation are increasingly consumed as cloud
services assembled from black-box APIs, and the acoustic channels feeding
these services are rarely clean. This manuscript contributes a controlled
benchmark, CascadeBench, that quantifies how eight canonical acoustic
channel degradations, including multi-talker babble noise at five
signal-to-noise ratios, reverberation, telephone narrowbanding, low-bitrate
coding, packet loss, clipping, and tempo distortion, propagate through the
recognition and translation stages of commercial speech services spanning
three architectural families. The study answers questions that we believe
fall squarely within the scope of Applied Acoustics and its acoustic signal
processing community: how do modern recognition services respond to
controlled acoustic degradation, and how do recognition errors induced by
the acoustic channel propagate into downstream translation quality.

The main findings are: (1) recognition error rises as a knee-shaped function
of noise, with the large-language-model recognisers crossing ten percent
error at noise levels 2.5 to 4 dB lower than the specialised streaming
system and failing below 0 dB by insertion-heavy hallucination that drives
character error rates above 100 percent; (2) cascade translation quality
falls linearly with recognition error rate at 0.44 to 0.54 BLEU points per
percentage point, with sentence-level bootstrap confidence intervals within
0.04 and a statistically zero intercept, across fifteen operating conditions
and three frontends; (3) end-to-end speech translation is not automatically
more robust than a well-frontended cascade, with the omni-modal path losing
a third of its BLEU at 0 dB while a streaming end-to-end service is the most
resilient; and (4) a dual-reference scoring protocol exposes and controls
the bias arising when machine translation is scored against
machine-generated references. All systems come from a single provider, so
the study is framed as a case study pending cross-provider replication.

All experiments were executed on free-tier API quotas with a fully seeded,
reproducible pipeline, and the complete benchmark recipe will be released.
The manuscript is not under consideration elsewhere, and the authors declare
no competing interests.

We suggest the following potential reviewers with expertise in robust speech
recognition and speech translation evaluation, should the editor find it
helpful: [reviewer suggestions to be completed by the corresponding author].

Thank you for your consideration.

Sincerely,
The Authors

---

## Highlights (3-5 bullets, max 100 characters each)

- Black-box case study of commercial speech APIs under eight acoustic degradations
- LLM recognisers tolerate 2.5 to 4 dB more noise before error reaches ten percent
- Below 0 dB, LLM recognisers hallucinate, driving error rates above 100 percent
- Translation quality falls 0.44 to 0.54 BLEU per point of recognition error
- Dual-reference protocol exposes machine-reference bias that inverts rankings

---

## Statement of Novelty and Significance (max 100 words)

Prior robustness benchmarks target open recognisers on recorded corpora and
stop at the transcription boundary. We provide the first controlled
measurement of how acoustic channel degradations propagate from recognition
into translation for commercial black-box speech APIs, covering three
recogniser families and both cascade and end-to-end translation paths. We
quantify family-level noise degradation gradients, a linear 0.47 to 0.66
BLEU per percentage point error pass-through rule, the reversal of
cascade-versus-end-to-end robustness under severe noise, and a
machine-reference scoring bias, with a fully seeded and reproducible recipe
that can be re-run as services evolve.
