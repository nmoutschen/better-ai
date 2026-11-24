#!/bin/sh
set -eu

proof_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
image=ghcr.io/bigtalk-org/docker-nagini@sha256:0a77b3dddfafb87393f2aef82e6ce8d29d37e5af95d7480d14f977e4f0b1fe3a
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
python3 "$proof_dir/extract_production_commit.py" > "$scratch/production_commit.py"

verify() {
    docker run --rm --platform linux/amd64 --network none --cap-drop ALL \
        --security-opt no-new-privileges --mount "type=bind,source=$proof_dir,target=/code,readonly" \
        --mount "type=bind,source=$scratch,target=/proof,readonly" "$image" "$@"
}

verify /proof/production_commit.py
verify /code/record_commit.py --select 'commit,compare_and_publish,publish,Record.__init__,UnitLock.invariant'

status=0
negative=$(verify /code/record_commit.py --select split_commit 2>&1) || status=$?
printf '%s\n' "$negative"
case "$status:$negative" in
    1:*'The precondition of method publish might not hold. Assertion record.snapshot == expected might not hold.'*)
        printf '%s\n' 'Split check and write rejected as expected.'
        ;;
    *)
        printf '%s\n' 'Expected Nagini to reject publication after releasing the lock.' >&2
        exit 1
        ;;
esac
