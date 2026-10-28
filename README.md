# MikołajRej

### From archival scans to readable text.

**English** · [Polski](README.pl.md)

Explore historical handwriting in a local web application. Browse scans, segment pages into lines, recognize the text and inspect each reading alongside the original image.

**[Download model + Diariusz LM](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main) · [Get the application](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr) · [Quick start](docs/QUICKSTART.md)**

[![MikołajRej: the application showing a historical scan and its reading](screenshots/app-reader.png)](screenshots/app-reader.png)

*The real application: scan and reading side by side, with linked line highlighting.*

## Read. Compare. Review.

- **Find your way through a collection** — scan gallery, rotation and batch selection.
- **Keep the page structure** — line segmentation, columns and reading order.
- **Compare readings** — RAW recognition, optional Diariusz LM and saved model versions.
- **Stay close to the source** — interactive scan-to-text reports, line highlighting and manual corrections.

## See it in action — 12 screens

Click a screen to open it at full size. The gallery combines supplied application views with saved readings of diary pages and historical codices.

| | |
|---|---|
| **01 · Interactive scan-to-text reader**<br>[![Interactive scan-to-text reader](screenshots/app-reader.png)](screenshots/app-reader.png) | **02 · Scan gallery and stored model runs**<br>[![Scan gallery and stored model runs](screenshots/app-gallery.png)](screenshots/app-gallery.png) |
| **03 · Archival register in the application**<br>[![Archival register in the application](screenshots/app-register.png)](screenshots/app-register.png) | **04 · Rybeńko diary · r01-R**<br>[![Rybeńko diary · r01-R](screenshots/reading-01.png)](screenshots/reading-01.png) |
| **05 · Rybeńko diary · r02-L**<br>[![Rybeńko diary · r02-L](screenshots/reading-02.png)](screenshots/reading-02.png) | **06 · Rybeńko diary · r02-R**<br>[![Rybeńko diary · r02-R](screenshots/reading-03.png)](screenshots/reading-03.png) |
| **07 · Psałterz floriański · saved line**<br>[![Psałterz floriański · saved line](screenshots/reading-04.png)](screenshots/reading-04.png) | **08 · Psałterz floriański · saved line**<br>[![Psałterz floriański · saved line](screenshots/reading-05.png)](screenshots/reading-05.png) |
| **09 · Rozmyślanie przemyskie · saved line**<br>[![Rozmyślanie przemyskie · saved line](screenshots/reading-06.png)](screenshots/reading-06.png) | **10 · Rozmyślanie przemyskie · saved line**<br>[![Rozmyślanie przemyskie · saved line](screenshots/reading-07.png)](screenshots/reading-07.png) |
| **11 · Ortyle prawa magdeburskiego · saved line**<br>[![Ortyle prawa magdeburskiego · saved line](screenshots/reading-08.png)](screenshots/reading-08.png) | **12 · Ortyle prawa magdeburskiego · saved line**<br>[![Ortyle prawa magdeburskiego · saved line](screenshots/reading-09.png)](screenshots/reading-09.png) |

*Recorded outputs, including errors. Original application views may show earlier versions. Saved E26 previews use known development examples, not an independent test. [Sources and reading provenance](screenshots/README.md).*

## Run it on your own computer

Get the [application code](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr) and the [model files](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main), then follow the [English quick start](docs/QUICKSTART.md). The full application targets Windows / Python 3.12 and defaults to CPU. This release provides local software and downloads; it does not run a hosted OCR service.

## Research and public-interest projects

Non-commercial scientific research and public-interest projects are welcome, **with attribution to Łukasz Rzepiński** and compliance with the licence. The author would be happy to hear how you use the project; notification is voluntary.

**Commercial use of covered rights requires prior contact and separate written permission:** [lukasz.rzepinski@gmail.com](mailto:lukasz.rzepinski@gmail.com). These are custom terms, **not MIT**; upstream permissions and public-domain material remain unaffected. [Terms](LICENSE) · [English translation](LICENSE.en.md).

## About the project and author

[zbiorycyfrowe.pl](https://zbiorycyfrowe.pl/) is a project for processing archival resources with artificial intelligence. MikołajRej supports recognition and transcription work on historical documents.

**Łukasz Rzepiński** is a Solution Architect working in clinical research, with previous experience in banking and telecommunications. He is the author of [ofertarium.pl](https://ofertarium.pl/), [lekoskop.pl](https://lekoskop.pl/), [ostint.pl](https://ostint.pl/) and [zrodlacyfrowe.pl](https://zrodlacyfrowe.pl/).

Contact: [lukasz.rzepinski@gmail.com](mailto:lukasz.rzepinski@gmail.com).

## Documentation

[Full model card and provenance](docs/MODEL_CARD.md) · [Evaluation and limitations](docs/EVALUATION.md) · [File and source notices](NOTICE.md) · [Checksums](SHA256SUMS).

Names, dates and digits still need human review. The detailed model card keeps the known-DEV caveats, source limitations and runtime verification scope; the screenshots are illustrative, not a new benchmark.


## Experimental E105 model

[Download E105](https://huggingface.co/lukaszrzepinski/MikolajRej/blob/main/MikolajRej-KRA-DateStrings-E105-step554359.mlmodel) · [Evaluation and provenance](docs/MODEL_E105.md). E105 is an additional candidate; E26 and the Diariusz language model remain available. Development scores are not independent test results.
