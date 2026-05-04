"""Local item store under ``~/.chaos/items/<uuid>/``.

An *item* is everything the seller has on disk for one car:

- ``manifest.json`` — canonical facets (make, model, year, mileage,
  pricing, description, tags). The on-the-wire NIP-99 event is
  derived from this.
- ``description.md`` — long-form description served inline on the
  ``view_listing`` MCP tool call.
- ``photos/`` — JPEGs/PNGs delivered as MCP ``ImageContent`` blocks
  from ``request_photos``.
- ``documents/`` — PDFs delivered as MCP ``EmbeddedResource`` blocks
  from ``request_inspection_report``.
- ``private/vin.txt`` — full VIN, never leaves the user's machine
  unless explicitly granted per-buyer (via ``request_vin``).

Per CLAUDE.md rule 5 ("No data custody"), the platform never sees
this data. ``catalog.py`` is local-only and explicitly does not have
any network surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True, slots=True)
class Item:
    """Canonical local representation of one listing.

    Attributes:
        item_id: UUID matching the NIP-99 ``d`` tag.
        title: Short title (e.g. ``"2018 Mazda 6 wagon"``).
        summary: One-line summary; goes into the public event.
        description: Long-form description, served inline on grant.
        make: Lowercase string per cars-pack tag schema.
        model: Lowercase string.
        year: 4-digit integer.
        body_type, fuel_type, transmission: enum strings.
        mileage_km: Integer kilometers.
        mileage_band: Bucketed band string (e.g. ``"50k-75k"``).
        price_amount, price_currency: Asking price.
        price_band: Bucketed band string.
        location: Region path (e.g. ``"EU/CZ/Prague"``).
        photos: Sorted list of photo paths.
        documents: Sorted list of document paths (PDFs).
        vin_full: Full VIN if known. Never auto-shared.
        bid_min_cents: Hard floor for negotiation.
        accepts_offer: Whether the seller is open to counter-offers.
        status: ``"active" | "reserved" | "sold" | "archived"``.
    """

    item_id: str
    title: str
    summary: str
    description: str
    make: str
    model: str
    year: int
    body_type: str
    fuel_type: str
    transmission: str
    mileage_km: int
    mileage_band: str
    price_amount: int
    price_currency: str
    price_band: str
    location: str
    photos: tuple[Path, ...] = field(default_factory=tuple)
    documents: tuple[Path, ...] = field(default_factory=tuple)
    vin_full: str | None = None
    bid_min_cents: int | None = None
    accepts_offer: bool = True
    status: str = "active"


class Catalog:
    """File-backed item catalog under ``items_dir``.

    All methods are synchronous and assume single-process access. If
    the seller plugin ever grows multi-process write paths, switch to
    flock'd JSON.
    """

    def __init__(self, items_dir: Path) -> None:
        """Initialize against an existing or new items directory.

        Args:
            items_dir: Filesystem root, e.g.
                       ``~/.chaos/items``.
        """
        self.items_dir = items_dir

    def load(self, item_id: str) -> Item:
        """Load the item with the given id.

        Args:
            item_id: UUID directory name under ``items_dir``.

        Returns:
            The ``Item`` parsed from ``manifest.json`` plus
            ``description.md`` and the photo / document directories.

        Raises:
            FileNotFoundError: if no directory exists for ``item_id``.
            ValueError: if ``manifest.json`` is malformed.
        """
        raise NotImplementedError("catalog.Catalog.load not implemented")

    def save(self, item: Item) -> None:
        """Persist an item to disk.

        Writes ``manifest.json`` and ``description.md``. Does not
        touch ``photos/`` or ``documents/`` — those are owned by the
        user's external workflow.

        Args:
            item: The item to save.

        Raises:
            OSError: on filesystem failure.
        """
        raise NotImplementedError("catalog.Catalog.save not implemented")

    def iter_items(self) -> Iterator[Item]:
        """Yield every item in the catalog, sorted by ``item_id``.

        Returns:
            Iterator over ``Item`` instances.
        """
        raise NotImplementedError("catalog.Catalog.iter_items not implemented")

    def photos_for(self, item_id: str, *, category: str | None = None) -> list[Path]:
        """List photo paths for an item, optionally filtered by category.

        Categories follow the cars-pack@1 ``request_photos(kinds=...)``
        argument values (``exterior``, ``interior``, ``engine_bay``,
        ``undercarriage``, ``license_plate_blurred``). The directory
        layout is ``photos/<category>/<index>.jpg``; un-categorized
        photos live directly under ``photos/``.

        Args:
            item_id: The item id.
            category: Optional category (e.g. ``"exterior"``).

        Returns:
            Sorted list of photo paths matching the category.
        """
        raise NotImplementedError("catalog.Catalog.photos_for not implemented")
