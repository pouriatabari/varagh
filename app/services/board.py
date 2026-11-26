"""The per-task board: draggable sticky notes."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import BoardItem

VALID_TYPES = ("sticky", "text")
VALID_COLORS = ("yellow", "green", "blue", "pink", "grey")


@dataclass(slots=True)
class BoardItemView:
    """A board item prepared for rendering."""

    id: int
    type: str
    content: str
    x: float
    y: float
    color: str


def list_items(session: Session, task_id: int) -> list[BoardItem]:
    """Return the board items of a task, oldest first."""
    query = select(BoardItem).where(BoardItem.task_id == task_id).order_by(BoardItem.id.asc())
    return list(session.scalars(query).all())


def create_item(
    session: Session,
    *,
    task_id: int,
    content: str,
    item_type: str = "sticky",
    color: str = "yellow",
    x: float = 0.0,
    y: float = 0.0,
) -> BoardItem:
    """Create a board item."""
    item = BoardItem(
        task_id=task_id,
        type=item_type if item_type in VALID_TYPES else "sticky",
        content=content,
        color=color if color in VALID_COLORS else "yellow",
        x=float(x),
        y=float(y),
    )
    session.add(item)
    session.flush()
    return item


def move_item(session: Session, item: BoardItem, x: float, y: float) -> BoardItem:
    """Move a board item to a new position."""
    item.x = float(x)
    item.y = float(y)
    session.flush()
    return item


def update_item(
    session: Session,
    item: BoardItem,
    *,
    content: str | None = None,
    color: str | None = None,
) -> BoardItem:
    """Update the text or the colour of a board item."""
    if content is not None:
        item.content = content
    if color is not None and color in VALID_COLORS:
        item.color = color
    session.flush()
    return item


def delete_item(session: Session, item: BoardItem) -> None:
    """Delete a board item."""
    session.delete(item)
    session.flush()
