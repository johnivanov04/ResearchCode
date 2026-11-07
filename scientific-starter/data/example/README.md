# Example input (illustrative)

`two_readings.csv` is **illustrative data, not a measurement**. The two values were chosen
so that the optical density doubles in exactly two hours, which makes the expected answer
easy to check by hand: a specific growth rate of ln(2) / 2 = 0.34657359 per hour and a
doubling time of 2 hours.

| Column               | Units         | Meaning                                      |
| -------------------- | ------------- | -------------------------------------------- |
| `time_h`             | hours         | Time of the reading                          |
| `od_blank_corrected` | dimensionless | Optical density with the medium blank removed |

Replace this directory with your own data. Keep raw instrument exports read-only (for
example in `data/raw/`), and record their checksums; `write_run_metadata` records the
SHA-256 checksum of every input file it is given.
