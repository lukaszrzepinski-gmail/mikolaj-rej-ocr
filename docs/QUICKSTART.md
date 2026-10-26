# MikołajRej: English quick start

[Model and LM files](https://huggingface.co/lukaszrzepinski/MikolajRej/tree/main) · [Application code](https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr) · [Model card](https://huggingface.co/lukaszrzepinski/MikolajRej)

## Requirements and installation

The complete local web application targets **Windows and Python 3.12**. It retains Windows-specific memory and process-priority checks. Linux/macOS support for the complete GUI is not claimed; the separate PAGE XML wrapper has its own documented input contract. The application runs on your computer, with CPU as the default. No paid server, subscription, hosted inference endpoint or GPU Space is required.

```powershell
git clone https://github.com/lukaszrzepinski-gmail/mikolaj-rej-ocr.git
cd mikolaj-rej-ocr
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

These are direct dependency pins rather than a complete transitive lockfile. This publication did not perform a fresh installation or full-page OCR in that new environment. The original model export used Python 3.12.13, Kraken 7.0.2, PyTorch 2.10.0+cu128, coremltools 9.0 and Pillow 12.3.0, with a prior two-line CPU smoke test. The proposed installation selects CPU wheels; do not treat that as independently verified end-to-end platform parity. Do not modify an active training environment to install this application.

## Download and verify models

From the HF Files tab, download `MikolajRej-KRA-K11-E26-step345005.mlmodel` and optionally `lm6B.bin`. Put them in the GitHub repository's `models/` directory. Recognition weights have SHA256 `871092c802375e0100c1b2efefb2dcf687b87022f2305723dfffb9aeef5e243d`; LM has SHA256 `7545861f8b82a5b4d8ecce74e057c720fadc7683c7aa2302bc63fd500b666bff`. The GUI export and public copy have different hashes because local paths were removed from metadata; weights and codec remain unchanged.

```powershell
python scripts/verify_models.py --directory models
python app/serwer_gui.py
```

Open http://127.0.0.1:5057 manually. `--open-browser` opens it only when explicitly requested. `REJ_MODEL_DIR` sets a different model directory; `REJ_PORT` sets the port. The application listens on loopback for one local session and is not a multi-user Internet service.

## Process scans

1. Select a working copy of a scan folder, choose images and correct rotation.
2. Choose automatic, single-column or two-column reading order. Run segmentation and inspect the line/column order.
3. Select E26 and run recognition. RAW is the initial default. Enable Diariusz LM only when a compatible KenLM binding and the LM file are available.
4. Review scan and text together. Compare stored models/LM variants, retain RAW and manually check names, dates and digits.

The app writes text, OCR JSON, segmentation previews, history, corrections and HTML reports beside your scans. Current text/report files may be replaced on a later run; history preserves earlier variants. Local logs and report registries can contain file paths and document history; they are not public examples. Use the supplied reference-free Polona examples for a public demonstration.

## Optional Diariusz LM

RAW recognition and segmentation do not require KenLM. Diariusz LM is a character 6-gram; the Python binding must be built with **MAX_ORDER >=6**. The original Windows environment used a local KenLM 0.2.0 build. Native DLL/PYD/SO files and the owner's environment are not distributed. [KenLM upstream](https://github.com/kpu/kenlm) documents Python builds and MAX_ORDER; an untested `pip install kenlm` should not be presented as a guaranteed Windows installer.

Reported settings are α=0.5, β=1, beam=64, cutoff=0.001 and temperature=1. LM may improve mean CER while changing a correct rare word, name or digit. Keep the RAW reading. The historical LM build corpus is incompletely documented, as disclosed in the model card.

## Command-line pipeline

Create `images.tsv` with one image per line: absolute image path, a tab, then rotation 0/90/180/270. From the code repository:

```powershell
python app/segment_preview.py --images images.tsv --preview-dir preview --device cpu --layout auto --cpu-workers 1
python app/ocr_batch.py --model models/MikolajRej-KRA-K11-E26-step345005.mlmodel --images images.tsv --preview-dir preview --device cpu --layout auto
python app/report_gen.py --folder SCANS --out SCANS/_RAPORT_OCR.html --model "MikołajRej E26 RAW"
```

Replace `SCANS` with your working folder. Once KenLM is prepared, append `--lm models/lm6B.bin --lm-name Diariusz --alpha 0.5 --beta 1 --beam 64` to the recognition command. Segmentation uses the separate BLLA model bundled with Kraken 7.0.2. It is not a new model trained by this project. Segment previews default to one geometry worker; model operations use two CPU threads and check available memory. These guards are not a measured maximum RAM guarantee. Optional local CUDA requires an explicitly configured cooperative `REJ_GPU_LOCK`; it does not discover every other GPU process automatically.

## Recognition from existing PAGE XML

The separate `scripts/recognize_page.py` wrapper takes one image and matching PAGE XML containing text-line `Coords` and `Baseline`; reference `TextEquiv` is not needed. Coordinates, image filename and dimensions must match. It adds no LM or text correction and exclusively creates a new output JSON:

```powershell
python scripts/recognize_page.py --model models/MikolajRej-KRA-K11-E26-step345005.mlmodel --model-sha256 871092c802375e0100c1b2efefb2dcf687b87022f2305723dfffb9aeef5e243d --image page.png --page-xml page.xml --output raw-predictions.json --threads 2
```

The wrapper does not perform automatic page segmentation. It preserves the pinned Kraken 7.0.2 interface and has not been executed with the model in a fresh installation for this publication. Syntax, metadata, file integrity, lightweight server configuration and reading-order checks passed; this is not a new accuracy benchmark.

## Use and attribution

Non-commercial scientific research and public-interest projects are allowed within the custom licence's scope, with attribution. Commercial use of the author's covered rights requires separate written permission: [lukasz.rzepinski@gmail.com](mailto:lukasz.rzepinski@gmail.com). The author would appreciate hearing how the project is used; notification is voluntary. Upstream rights, public-domain material and legal exceptions remain unaffected. See the repository's LICENSE and LICENSE.en.md; these terms are not MIT.
