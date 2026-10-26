# MikołajRej OCR

**English** · [Polski](README.pl.md)

MikołajRej helps researchers and archival projects read and process historical documents with AI. It turns local scans into reviewable text while keeping each reading connected to the image. The goal is to make historical sources easier to transcribe and work with, with human review of names, dates, digits and difficult passages.

The local web application includes an image gallery, rotation, page-to-line segmentation, column-aware reading order, recognition, optional Diariusz LM decoding, saved result history, model/LM comparisons, an interactive scan-to-text report and manual line corrections.

## Get the model and run locally

- [MikołajRej model weights and Diariusz LM on Hugging Face](https://huggingface.co/lukaszrzepinski/MikolajRej).
- [English installation and pipeline quick start](docs/QUICKSTART.md).
- [English model card, evaluation and limitations](docs/MODEL_CARD.md).
- [Scan → saved RAW examples](examples/README.md) and [static showcase source](docs/showcase/index.html).
- Original detailed Polish instructions: [web app and pipeline](docs/WEB_APP.md), [PAGE XML wrapper](docs/LOCAL_INFERENCE.md), [Diariusz LM](docs/DIARIUSZ_LM.md), [evaluation](docs/EVALUATION.md), [data provenance](docs/DATA_PROVENANCE.md).

The full app targets Windows and Python 3.12, defaults to CPU and runs at http://127.0.0.1:5057 . Download the model files to `models/`, verify them with `python scripts/verify_models.py --directory models`, then start `python app/serwer_gui.py` in a prepared environment. The quick start explains dependencies, optional KenLM and the limits of testing. Source publication does not deploy an online OCR service.

## Results and limitations

E26 achieved **7.19% macro CER on RAW110 pseudo DEV used for epoch selection**. The combined system with Diariusz LM achieved 5.84% macro CER on the same set. This is not independent human-gold evaluation. The 1.314% Diariusz result refers to only 24 known lines; the separate known D17 diagnostic is 9.95% RAW and 8.73% with LM, with reference limitations. Accuracy on genuinely unseen writers and books, and reliable preservation of names/digits, remain unverified. The model card describes provenance and incomplete historical corpus documentation.

## Research use, public-interest projects and attribution

Non-commercial scientific research and public-interest projects are welcome, subject to the licence and attribution requirements. Credit **Łukasz Rzepiński**, retain the licence and applicable third-party notices, and identify your modifications.

**Commercial use of rights covered by this project's licence requires prior contact and separate written permission from the author.** The author would be happy to hear how you use the project; sending an update is appreciated, but **voluntary**.

These are custom terms, **not the MIT licence**. They apply only to rights the author actually holds. They do not remove upstream permissions, restrict public-domain material, or override uses permitted by law. See [LICENSE](LICENSE), its [English translation](LICENSE.en.md), and [NOTICE.md](NOTICE.md).

## Related archival project

[zbiorycyfrowe.pl](https://zbiorycyfrowe.pl/) is a project for processing archival resources with artificial intelligence. MikołajRej supports recognition and transcription work on historical documents.

## Author and contact

**Łukasz Rzepiński** is a Solution Architect working in clinical research, with previous experience in banking and telecommunications. He is the author of [ofertarium.pl](https://ofertarium.pl/), [lekoskop.pl](https://lekoskop.pl/), [ostint.pl](https://ostint.pl/) and [zrodlacyfrowe.pl](https://zrodlacyfrowe.pl/).

Contact, including requests for commercial-use permission: [lukasz.rzepinski@gmail.com](mailto:lukasz.rzepinski@gmail.com).
