# Superseded freeze records

Each file here is a byte-for-byte copy of a file as it was frozen before a later amendment, kept
for audit. A test (`tests/test_protocol_amendment_1_5.py`) checks every copy against the hashes in
the freeze record it belongs to.

| File | What it is |
| --- | --- |
| `FREEZE-1.4.json` | The freeze record of protocol 1.4 (combined SHA-256 `b910a7b7afd0a1fd…`), under which the six pilot trials and the first confirmatory trial (`serial-dilution--B--r01`) were run and evaluated |
| `PROTOCOL-1.4.md` | The protocol, version 1.4 |
| `experiment-1.4.json` | The configuration, version 1.4 |

The current protocol is [`docs/PROTOCOL.md`](../docs/PROTOCOL.md); its section 13 lists every
amendment, including version 1.5, which superseded these files on 2026-11-16.
