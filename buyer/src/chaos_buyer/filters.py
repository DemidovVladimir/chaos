"""Translate user wants into Nostr REQ filters.

Per ``PROTOCOL.md`` § "Subscriptions", REQ filters reference the
cars-pack tag schema. Discrete tag matches happen on the relay's
index. Numeric ranges that don't fit discrete buckets (precise year,
exact mileage) are expressed as the set of acceptable bucket values.
Buyer-side post-filtering handles whatever the relay can't.
"""
from __future__ import annotations

from dataclasses import dataclass


# Canonical year-tag values are emitted as 4-digit strings.
def year_range_to_set(low: int, high: int) -> tuple[str, ...]:
    """Expand a closed year range into the discrete tag-value set.

    Args:
        low: Inclusive lower year (e.g. 2015).
        high: Inclusive upper year (e.g. 2020).

    Returns:
        Tuple of 4-digit year strings.

    Raises:
        ValueError: if ``low > high`` or values are nonsensical.
    """
    raise NotImplementedError("filters.year_range_to_set not implemented")


# Canonical mileage-band buckets per the cars-pack tag schema.
MILEAGE_BANDS: tuple[str, ...] = (
    "0-10k",
    "10k-25k",
    "25k-50k",
    "50k-75k",
    "75k-100k",
    "100k-150k",
    "150k+",
)


def mileage_range_to_bands(low_km: int, high_km: int) -> tuple[str, ...]:
    """Map a kilometer range to the matching mileage-band set.

    Args:
        low_km: Inclusive lower bound.
        high_km: Inclusive upper bound.

    Returns:
        Tuple of band names that overlap the range.
    """
    raise NotImplementedError("filters.mileage_range_to_bands not implemented")


@dataclass(frozen=True, slots=True)
class UserWant:
    """A high-level shape describing what the user wants.

    Attributes:
        make: Optional list of makes to match.
        model: Optional list of models.
        year_range: Optional ``(low, high)`` inclusive year range.
        body_type, fuel_type, transmission: Optional enum lists.
        location_prefix: Optional list of location prefixes
                         (e.g. ``"EU/CZ/%"``).
        price_band: Optional list of price-band names.
        since_days: Optional integer; restricts to events
                    published within the last N days.
    """

    make: tuple[str, ...] = ()
    model: tuple[str, ...] = ()
    year_range: tuple[int, int] | None = None
    body_type: tuple[str, ...] = ()
    fuel_type: tuple[str, ...] = ()
    transmission: tuple[str, ...] = ()
    location_prefix: tuple[str, ...] = ()
    price_band: tuple[str, ...] = ()
    since_days: int | None = None


def from_user_want(want: UserWant) -> dict:
    """Build a NIP REQ filter dict from a ``UserWant``.

    Args:
        want: The user's parsed wants.

    Returns:
        A filter dict matching the shape in PROTOCOL.md.

    Raises:
        ValueError: on contradictory fields (e.g. empty make list
            but model list present that doesn't match any registered
            make).
    """
    raise NotImplementedError("filters.from_user_want not implemented")


def to_pynostr_filters(filter_dict: dict) -> object:
    """Convert a plain filter dict to ``pynostr.filters.FiltersList``.

    Args:
        filter_dict: As returned by ``from_user_want``.

    Returns:
        A ``pynostr.filters.FiltersList`` instance.
    """
    raise NotImplementedError("filters.to_pynostr_filters not implemented")
