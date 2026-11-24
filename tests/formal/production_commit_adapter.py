"""Filesystem assumptions for the commit function copied from production."""

from typing import Optional

from nagini_contracts.contracts import Acc, ContractOnly, Ensures, Old, Pure, Requires, Result


@Pure
@ContractOnly
def same_contents(current: Optional[bytes], expected: Optional[bytes]) -> bool:  # noqa: UP045
    """Abstract equality of complete snapshots, including an absent file."""
    pass


class _RecordFile:
    """Model a target held under its unit's exclusive directory lock."""

    def __init__(self, contents: Optional[bytes]) -> None:  # noqa: UP045
        Ensures(Acc(self.contents) and self.contents is contents)
        self.contents: Optional[bytes] = contents  # noqa: UP045

    @ContractOnly
    def matches(self, expected: Optional[bytes]) -> bool:  # noqa: UP045
        Requires(Acc(self.contents))
        Ensures(Acc(self.contents) and self.contents is Old(self.contents))
        Ensures(Result() == same_contents(self.contents, expected))
        pass

    def publish(self, replacement: bytes) -> None:
        Requires(Acc(self.contents))
        Ensures(Acc(self.contents) and self.contents is replacement)
        self.contents = replacement
