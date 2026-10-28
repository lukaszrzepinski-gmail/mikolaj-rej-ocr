# MikołajRej K11 E105 — candidate model

This is an additional experimental Kraken recognition model, trained from the previous MikołajRej line. It does not replace the existing E26 model or the Diariusz language model. Use it with Kraken 7 and compare its output with other versions for the intended documents.

- File: `MikolajRej-KRA-DateStrings-E105-step554359.mlmodel` (16437152 bytes).
- SHA-256: `2160f39aa76c7f1b2d966c21112161c75cfb5c6b25ae3555825e651714c4f034`.
- Source training checkpoint SHA-256: `c31996e83619a731f4d708c12de9ea68c3c766ccf5de983b935686292983f306`.
- The auxiliary HANA surname head is not part of this recognition export.
- Metadata was sanitized to remove local file paths; network payload and codec are unchanged relative to the locally verified GUI export.

## Evaluation (development data, RAW without LM)

- Date Strings development years: 518/615 exact strings. The set consists of four-digit years; this is not full-date accuracy.
- Diariusz17: 90 digit-character edit errors; the page-level reference is not fully human-verified and digits predicted in place of letters are counted.
- Brzeżany page 0290: 3 digit-character errors; the benchmark contains ten lines and is not an independent book-level test.
- Kraśnik development: 1994 character errors / 12888 characters; original line crops can include neighboring writing.
- Brzeżany checked date crops: 5/8 exact full strings.

These DEV results informed selection. They do not establish independent test performance or that E105 improves every document type. Names, numbers and dates require human review. No E105 comparison with the Diariusz LM is claimed.

## Sources and limitations

E105 continues from E26 and includes mixed replay, selected Kraśnik crops, human-reviewed numeric lines, Swedish Date Strings year images, and HANA auxiliary surname training. Earlier data may have model-generated references. The user-supplied Date Strings archive contained no licence file; its redistribution terms and the implications for trained weights have not been verified. HANA source is identified as CC BY-NC-SA 4.0: Christian M. Dahl, Torben S. D. Johansen, Emil N. Sørensen and Simon Friis Wittrock, DOI 10.1016/j.eeh.2022.101473. The original McCATMuS upstream and other data notices remain applicable as described in the existing repository. The legal status of weights derived from those datasets has not been determined. No training images, references, local paths or training checkpoints are included in this release.

Existing project licence applies only to the rights actually held by the author and does not override upstream rights. See `NOTICE.md`, `LICENSE` and the E26 documentation.
