# MikołajRej — E26 and Diariusz LM

**English** · [Polski](MODEL_CARD.pl.md)

MikołajRej is an experimental AI-assisted tool for reading and processing historical archival material, particularly Polish and Latin handwriting. Its purpose is to make historical sources easier to transcribe, inspect and work with while preserving a link between the scan and the machine reading.

The full local web application provides an image gallery, rotation, page segmentation into text lines, column-aware reading order, recognition, an optional Diariusz language model, saved result history, comparisons and an interactive scan-to-text report. Outputs require human review, especially names, dates, digits and marginal notes.

## Downloads and application code

- [Model weights, Diariusz LM and file checksums](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main).
- [Local web application, segmentation and processing pipeline on GitHub](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr).
- [English quick start](QUICKSTART.md).
- [Reference-free scan → saved RAW examples](../examples/README.md) (Polish descriptions).

This release distributes downloadable files and code for local use. It does not provide a hosted OCR endpoint or an online processing service.

## Released artifacts

| File | Bytes | SHA256 |
|---|---:|---|
| MikolajRej-KRA-K11-E26-step345005.mlmodel | 16,437,242 | `871092c802375e0100c1b2efefb2dcf687b87022f2305723dfffb9aeef5e243d` |
| lm6B.bin | 61,757,330 | `7545861f8b82a5b4d8ecce74e057c720fadc7683c7aa2302bc63fd500b666bff` |

E26/global step 345005 was selected on the declared development diagnostic after K11 ended naturally at E31/global389675. Local file paths were removed from the publication copy's metadata. The serialized network, codec and remaining processing settings are byte-identical to the previously checked GUI export. The original GUI export has a different checksum, beginning `195ea0b2`. Full training checkpoints and optimizer states are not distributed. See provenance.json.

## Evaluation: known pseudo development data

**RAW110 is pseudo DEV used to select the epoch, not an independent human-gold test.** It contains 110 known lines and 4,114 reference characters. References have inherited pseudo/silver provenance. Earlier model and LM exposure to the sources has not been ruled out.

| Domain | Lines | RAW, no LM | KorBa comparison | Diariusz LM |
|---|---:|---:|---:|---:|
| CDIAL letters | 37 | 8.922% | 8.383% | 4.611% |
| Diariusz | 24 | 3.067% | 3.395% | 1.314% |
| Psałterz | 17 | 7.872% | 10.787% | 8.163% |
| Rozmyślanie | 24 | 11.285% | 17.167% | 10.324% |
| Ortyle | 8 | 4.789% | 8.451% | 4.789% |

RAW macro CER is **7.186787%**, and micro CER is **315/4114 = 7.656782%**. With Diariusz LM, system macro CER is **5.840251%**, and micro CER is **220/4114 = 5.347594%**. Macro CER is the unweighted mean of five within-domain micro CERs. The LM result describes the combined system, not the recognition weights alone. KorBa is a comparison column and is not part of the distributed artifacts.

The 1.314% Diariusz result covers **24 lines and 913 characters**, not 17 full pages. On the separate, known D17 diagnostic (17 pages, 17,503 NFC characters), RAW CER is **1742/17503 = 9.952580%**, and Diariusz LM CER is **1528/17503 = 8.729932%**. The D17 reference was prepared by Claude and viewed by the owner; independent character-by-character human correction has not been documented. Marginalia and additions are incomplete, and all 495 segmentation fields were retained. This is also not an independent human-gold benchmark.

RAW110 includes only nine reference digits in three sequences. Digit character errors are 4/9 RAW and 0/9 with Diariusz LM; this is insufficient to establish date-reading accuracy. Proper names were not annotated, so no name-preservation score is claimed. LM improved average CER but worsened Psałterz, and can change correct rare names or digits.

Reported LM settings: α=0.5, β=1, beam=64, cutoff=0.001, temperature=1, using the same CTC forward outputs. Evaluation normalizes to NFC and collapses whitespace; LM tokenization internally uses NFD. The target of CER ≤4% for Diariusz and <8% for genuinely unseen sources with name/digit protection remains **unverified**. Detailed original reports: [EVALUATION.md](EVALUATION.md) (Polish) and metrics.json.

## Provenance and training

The named base is **McCATMuS_nfd_nofix_V1**, Alix Chagué, with Thibault Clérice, Ariane Pinche and Simon Gabay; [Zenodo record / DOI 10.5281/zenodo.13788177](https://doi.org/10.5281/zenodo.13788177), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Subsequent adaptations include Argon/Rej, bulk training and K11 continuation. The historical checksum of the exact first base-model input and complete historical source membership have not been recovered.

The internally admitted adaptation corpus comprised 71,470 lines, predominantly pseudo-labelled: 71,243 historical pseudo-labelled lines, 4 inherited owner-approved full lines, 54 silver lines and 169 assistant-silver experimental lines. Sources include CDIAL/TsDIAL letters, Diariusz, Psałterz, Rozmyślanie, Ortyle and small additional cohorts. These categories do not imply independently verified human transcription. Later Kraśnik/HANA experiments are separate and are not this E26 release.

The owner identifies the Diariusz source as Michał Kazimierz Radziwiłł “Rybeńko”'s diary, held by AGAD, Radziwiłł Archive VI, II-80a, and in the public domain. [AGAD archive description](https://agad.gov.pl/?page_id=866). The exact connection between the historical lm6B.bin and its build corpus is incompletely documented; older scripts also refer to other material. The historical manuscript, modern editions and later transcriptions are separate sources. We do not claim a reconstructed exact LM corpus, verified DEV/TEST independence, or a complete rights register for every additional training source. [DATA_PROVENANCE.md](DATA_PROVENANCE.md) gives the detailed original audit in Polish.

The three Polona examples come from objects marked public domain by their source manifests. They are known pseudo DEV lines, selected by the first ID in each of three domains rather than by perfect accuracy. Only saved RAW predictions and geometry are distributed, without reference transcriptions. Their PAGE-to-full-spread transformations have not all been recovered and are not guessed.

## Runtime and limitations

The recognition file is a Kraken `.mlmodel`, not a Transformers model. The observed runtime used Python 3.12, Kraken 7.0.2 and PyTorch 2.10.0. Input contract: grayscale L, baseline segmentation, network height 120, legacy polygons false, 293 codec symbols plus the CTC blank. The full application retains Windows memory/priority checks, defaults to CPU and uses the BLLA segmentation model from the Kraken installation. BLLA is a separate upstream model, not a newly trained MikołajRej segmenter.

Diariusz LM is an optional character KenLM 6-gram used after recognition forward passes. It needs a compatible Python KenLM binding built with MAX_ORDER at least 6. The original environment used a local KenLM 0.2.0 Windows build; no ready-made native extension or guaranteed one-command Windows installer is included.

The new package was checked for syntax, metadata, checksums, lightweight server behaviour and reading order without loading ML frameworks. The original export had a prior CPU smoke test on two known lines. The cleaned copy was checked by byte identity outside the stated metadata edit; fresh OCR and a clean dependency installation were not performed for this publication. Segmentation errors, wrong column order, rotation and missing annotations can affect results. Keep the original scan and RAW output and review the reading manually.

## Research use, public-interest projects and attribution

Non-commercial scientific research and public-interest projects are welcome, subject to the licence and attribution requirements. Credit **Łukasz Rzepiński**, retain the licence and applicable third-party notices, and identify your modifications.

**Commercial use of rights covered by this project's licence requires prior contact and separate written permission from the author.** The author would be happy to hear how you use the project; sending an update is appreciated, but **voluntary**.

These are custom terms, **not the MIT licence**. They apply only to rights the author actually holds. They do not remove upstream permissions, restrict public-domain material, or override uses permitted by law. See [LICENSE](../LICENSE), its [English translation](../LICENSE.en.md), and [NOTICE.md](../NOTICE.md).

## Related archival project

[zbiorycyfrowe.pl](https://zbiorycyfrowe.pl/) is a project for processing archival resources with artificial intelligence. MikołajRej supports recognition and transcription work on historical documents.

## Author and contact

**Łukasz Rzepiński** is a Solution Architect working in clinical research, with previous experience in banking and telecommunications. He is the author of [ofertarium.pl](https://ofertarium.pl/), [lekoskop.pl](https://lekoskop.pl/), [ostint.pl](https://ostint.pl/) and [zrodlacyfrowe.pl](https://zrodlacyfrowe.pl/).

Contact, including requests for commercial-use permission: [lukasz.rzepinski@gmail.com](mailto:lukasz.rzepinski@gmail.com).
