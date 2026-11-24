"""Nagini model of one file and the directory lock that protects publication."""

from nagini_contracts.contracts import Acc, Ensures, Implies, Old, Predicate, Requires, Result
from nagini_contracts.lock import Lock
from nagini_contracts.obligations import Level, MustTerminate, WaitLevel


class Record:
    """The file's complete visible snapshot, treated as one value."""

    def __init__(self, snapshot: str) -> None:
        Ensures(Acc(self.snapshot) and self.snapshot == snapshot)
        self.snapshot: str = snapshot


class UnitLock(Lock[Record]):
    @Predicate
    def invariant(self) -> bool:
        return Acc(self.get_locked().snapshot)


def publish(record: Record, expected: str, replacement: str) -> None:
    """Model publication of complete replacement bytes by the filesystem adapter."""
    Requires(Acc(record.snapshot) and record.snapshot == expected)
    Requires(MustTerminate(1))
    Ensures(Acc(record.snapshot) and record.snapshot == replacement)
    record.snapshot = replacement


def compare_and_publish(record: Record, expected: str, replacement: str) -> bool:
    """Return False on a stale snapshot, otherwise publish while still holding the lock."""
    Requires(Acc(record.snapshot))
    Requires(MustTerminate(2))
    Ensures(Acc(record.snapshot))
    Ensures(Result() == (Old(record.snapshot) == expected))
    Ensures(Implies(Result(), record.snapshot == replacement))
    Ensures(Implies(not Result(), record.snapshot == Old(record.snapshot)))
    if record.snapshot != expected:
        return False
    publish(record, expected, replacement)
    return True


def commit(lock: UnitLock, record: Record, expected: str, replacement: str) -> bool:
    """Keep comparison and publication in the same critical section."""
    Requires(lock.get_locked() is record)
    Requires(WaitLevel() < Level(lock))
    lock.acquire()
    committed = compare_and_publish(record, expected, replacement)
    lock.release()
    return committed


def split_commit(lock: UnitLock, record: Record, expected: str, replacement: str) -> bool:
    """Negative control: even separately protected steps permit an intervening writer."""
    Requires(lock.get_locked() is record)
    Requires(WaitLevel() < Level(lock))
    lock.acquire()
    current = record.snapshot == expected
    lock.release()
    if not current:
        return False
    lock.acquire()
    publish(record, expected, replacement)  # Nagini must reject this precondition.
    lock.release()
    return True
