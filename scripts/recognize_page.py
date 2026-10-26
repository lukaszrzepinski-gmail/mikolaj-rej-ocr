"""Local CPU recognition of an image with its existing PAGE XML baselines.

Uses the Kraken 7.0.2 legacy recognition interface used by the export smoke
check. No downloads, automatic segmentation, language model, or corrections.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"Not a regular file: {value}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", type=existing_file, required=True)
    parser.add_argument("--model-sha256", required=True,
                        help="SHA256 of the exact model file, from its release manifest")
    parser.add_argument("--image", type=existing_file, required=True)
    parser.add_argument("--page-xml", type=existing_file, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New JSON file; existing files are never overwritten")
    parser.add_argument("--threads", type=int, choices=range(1, 9), default=2)
    args = parser.parse_args()

    if args.model.suffix.lower() != ".mlmodel":
        parser.error("--model must be the published recognition .mlmodel")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.model_sha256):
        parser.error("--model-sha256 must have 64 hexadecimal characters")
    model_digest = sha256(args.model)
    if model_digest != args.model_sha256.lower():
        parser.error("Model SHA256 does not match; inference has not started")
    output = args.output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        parser.error("Output already exists; choose a new file")
    if not output.parent.is_dir():
        parser.error("Output parent directory must already exist")

    xml_data = args.page_xml.read_bytes()
    if b"<!DOCTYPE" in xml_data or b"<!ENTITY" in xml_data:
        parser.error("PAGE XML with DTD/entity declarations is not supported")
    document = ET.fromstring(xml_data)
    page = document.find(".//{*}Page")
    if page is None:
        parser.error("Expected a PAGE XML document with one Page element")
    if len(document.findall(".//{*}Page")) != 1:
        parser.error("Only one Page per XML input is supported")
    xml_image_name = page.get("imageFilename")
    if not xml_image_name:
        parser.error("PAGE XML requires imageFilename")
    xml_image = (args.page_xml.parent / xml_image_name).resolve(strict=True)
    if xml_image != args.image:
        parser.error("PAGE imageFilename must resolve to --image")
    try:
        expected_size = (int(page.attrib["imageWidth"]),
                         int(page.attrib["imageHeight"]))
    except (KeyError, ValueError):
        parser.error("PAGE XML requires positive imageWidth/imageHeight")
    if min(expected_size) < 1:
        parser.error("PAGE XML requires positive imageWidth/imageHeight")
    if importlib.metadata.version("kraken") != "7.0.2":
        parser.error("This wrapper requires kraken==7.0.2")

    # Set before importing the framework. Device selection remains explicitly CPU.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS"):
        os.environ[name] = str(args.threads)
    import torch
    from PIL import Image
    from kraken import rpred
    from kraken.lib import models
    from kraken.lib.xml import XMLPage

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(args.threads)
    loaded = models.load_any(str(args.model), train=False, device="cpu")
    model_type = loaded.nn.model_type
    if model_type != "recognition" and model_type != ["recognition"]:
        raise ValueError("Expected a recognition model")
    if loaded.nn.one_channel_mode != "L" or loaded.nn.seg_type != "baselines":
        raise ValueError("Expected model input contract L/baselines")
    parsed_page = XMLPage(str(args.page_xml))
    lines = parsed_page.to_container()
    if lines.type != "baselines" or not lines.lines:
        raise ValueError("PAGE XML must contain baseline text lines")
    line_ids = [line.id for line in lines.lines]
    if len(line_ids) != len(set(line_ids)):
        raise ValueError("PAGE XML line identifiers must be unique")
    for line in lines.lines:
        if not line.baseline or len(line.baseline) < 2 or not line.boundary:
            raise ValueError(f"Missing baseline or boundary for line {line.id}")
    with Image.open(args.image) as image:
        if image.size != expected_size or parsed_page.image_size != image.size:
            raise ValueError("PAGE dimensions do not match the supplied image")
        with torch.inference_mode():
            records = list(rpred.rpred(loaded, image.convert("RGB"), lines,
                                      pad=16, bidi_reordering=True,
                                      no_legacy_polygons=False))
    if len(records) != len(line_ids):
        raise RuntimeError("Recognizer output count differs from PAGE line count")
    result = {
        "model_sha256": model_digest,
        "image_sha256": sha256(args.image),
        "page_xml_sha256": hashlib.sha256(xml_data).hexdigest(),
        "kraken_version": importlib.metadata.version("kraken"),
        "torch_version": importlib.metadata.version("torch"),
        "device": "cpu",
        "decoder": "Kraken default greedy CTC; no external LM",
        "normalization_or_correction": "none added by this wrapper",
        "use_legacy_polygons": loaded.nn.use_legacy_polygons,
        "lines": [{"id": line_id, "prediction": record.prediction}
                  for line_id, record in zip(line_ids, records)],
    }
    # Exclusive creation is also checked at write time to prevent an overwrite race.
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"Saved {len(records)} line predictions to {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, ET.ParseError,
            importlib.metadata.PackageNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
