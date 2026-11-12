# Evaluation sandbox for the ResearchCode Phase 4 experiment.
#
# Runs generated (untrusted) code. The isolation itself is applied by `docker run`
# (see rc_experiments/sandbox.py): no network, read-only root file system, non-root user,
# all capabilities dropped, no-new-privileges, CPU/memory/process limits, and a
# size-limited /tmp. This image only provides Python 3.12 with exactly the packages
# submissions may use (NumPy, SciPy) plus pytest and Hypothesis for running their own tests.
#
# Build: rc-exp build-images   (tag researchcode-eval-sandbox:1)

# python:3.12.14-slim-bookworm, pinned by digest
FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

# Exported from experiments/uv.lock (dependency group "sandbox"); every file is hash-checked.
COPY requirements.txt /opt/requirements.txt
RUN pip install --no-cache-dir --no-deps --require-hashes --only-binary=:all: -r /opt/requirements.txt \
    && pip check

USER 65534:65534
WORKDIR /tmp
