"""Shared Chess rules helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


BOARD_SIZE = 8
WHITE = "white"
BLACK = "black"
PIECE_KINDS: Tuple[str, ...] = ("king", "queen", "rook", "bishop", "knight", "pawn")
NON_KING_PIECE_KINDS: Tuple[str, ...] = ("queen", "rook", "bishop", "knight", "pawn")

Coord = Tuple[int, int]
Board = Tuple[Tuple["ChessPiece | None", ...], ...]


@dataclass(frozen=True)
class ChessPiece:
    """One visible chess piece."""

    color: str
    kind: str


def opponent(color: str) -> str:
    """Return the opposite chess color."""

    return BLACK if str(color) == WHITE else WHITE


def color_name(color: str) -> str:
    """Return a prompt-facing color name."""

    return "White" if str(color) == WHITE else "Black"


def piece_name(piece: ChessPiece) -> str:
    """Return a prompt-facing piece name."""

    return f"{color_name(piece.color)} {piece.kind}"


def coord_to_cell_id(coord: Coord) -> str:
    """Return one stable board-cell id for a coordinate."""

    return f"cell_r{int(coord[0])}_c{int(coord[1])}"


def piece_to_entity_id(coord: Coord, piece: ChessPiece) -> str:
    """Return one stable piece entity id for a coordinate."""

    return f"piece_{piece.color}_{piece.kind}_r{int(coord[0])}_c{int(coord[1])}"


def in_bounds(row: int, col: int) -> bool:
    """Return whether one board coordinate lies inside the 8 by 8 board."""

    return 0 <= int(row) < BOARD_SIZE and 0 <= int(col) < BOARD_SIZE


def empty_board() -> Board:
    """Return an empty 8 by 8 chess board."""

    return tuple(tuple(None for _ in range(BOARD_SIZE)) for _ in range(BOARD_SIZE))


def freeze_board(board: Sequence[Sequence[ChessPiece | None]]) -> Board:
    """Freeze one mutable board into the canonical tuple representation."""

    return tuple(tuple(cell for cell in row) for row in board)


def occupied_coords(board: Sequence[Sequence[ChessPiece | None]]) -> Tuple[Coord, ...]:
    """Return all occupied board coordinates in row-major order."""

    coords: List[Coord] = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] is not None:
                coords.append((int(row), int(col)))
    return tuple(coords)


def occupied_piece_count(board: Sequence[Sequence[ChessPiece | None]]) -> int:
    """Return the total number of visible pieces on one board."""

    return len(occupied_coords(board))


def serialize_board(board: Sequence[Sequence[ChessPiece | None]]) -> list[list[str | None]]:
    """Return a JSON-friendly board representation."""

    rows: list[list[str | None]] = []
    for row in board:
        rows.append([None if piece is None else f"{piece.color}_{piece.kind}" for piece in row])
    return rows


def _ray_destinations(
    board: Sequence[Sequence[ChessPiece | None]],
    coord: Coord,
    piece: ChessPiece,
    directions: Iterable[Tuple[int, int]],
) -> Tuple[Coord, ...]:
    """Return pseudo-legal destinations along sliding-piece rays."""

    out: List[Coord] = []
    row, col = int(coord[0]), int(coord[1])
    for dr, dc in directions:
        r = int(row + dr)
        c = int(col + dc)
        while in_bounds(r, c):
            occupant = board[r][c]
            if occupant is None:
                out.append((int(r), int(c)))
            else:
                if str(occupant.color) != str(piece.color):
                    out.append((int(r), int(c)))
                break
            r += int(dr)
            c += int(dc)
    return tuple(out)


def piece_move_destinations(
    board: Sequence[Sequence[ChessPiece | None]],
    coord: Coord,
    *,
    include_pawn_double_step: bool = True,
) -> Tuple[Coord, ...]:
    """Return normal one-move destinations for a piece, excluding castling and en passant."""

    row, col = int(coord[0]), int(coord[1])
    piece = board[row][col]
    if piece is None:
        return ()
    kind = str(piece.kind)
    if kind == "queen":
        return _ray_destinations(
            board,
            coord,
            piece,
            ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)),
        )
    if kind == "rook":
        return _ray_destinations(board, coord, piece, ((-1, 0), (1, 0), (0, -1), (0, 1)))
    if kind == "bishop":
        return _ray_destinations(board, coord, piece, ((-1, -1), (-1, 1), (1, -1), (1, 1)))
    if kind == "knight":
        moves: List[Coord] = []
        for dr, dc in ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)):
            r = int(row + dr)
            c = int(col + dc)
            if not in_bounds(r, c):
                continue
            occupant = board[r][c]
            if occupant is None or str(occupant.color) != str(piece.color):
                moves.append((int(r), int(c)))
        return tuple(moves)
    if kind == "king":
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if int(dr) == 0 and int(dc) == 0:
                    continue
                r = int(row + dr)
                c = int(col + dc)
                if not in_bounds(r, c):
                    continue
                occupant = board[r][c]
                if occupant is None or str(occupant.color) != str(piece.color):
                    moves.append((int(r), int(c)))
        return tuple(moves)
    if kind == "pawn":
        moves = []
        direction = -1 if str(piece.color) == WHITE else 1
        start_row = 6 if str(piece.color) == WHITE else 1
        one_row = int(row + direction)
        if in_bounds(one_row, col) and board[one_row][col] is None:
            moves.append((int(one_row), int(col)))
            two_row = int(row + (2 * direction))
            if (
                bool(include_pawn_double_step)
                and int(row) == int(start_row)
                and in_bounds(two_row, col)
                and board[two_row][col] is None
            ):
                moves.append((int(two_row), int(col)))
        for dc in (-1, 1):
            r = int(row + direction)
            c = int(col + dc)
            if not in_bounds(r, c):
                continue
            occupant = board[r][c]
            if occupant is not None and str(occupant.color) != str(piece.color):
                moves.append((int(r), int(c)))
        return tuple(moves)
    raise ValueError(f"unsupported chess piece kind: {kind}")


def pawn_attack_squares(coord: Coord, color: str) -> Tuple[Coord, ...]:
    """Return attacked squares for a pawn regardless of occupancy."""

    row, col = int(coord[0]), int(coord[1])
    direction = -1 if str(color) == WHITE else 1
    squares: List[Coord] = []
    for dc in (-1, 1):
        r = int(row + direction)
        c = int(col + dc)
        if in_bounds(r, c):
            squares.append((int(r), int(c)))
    return tuple(squares)


def piece_attacks_square(
    board: Sequence[Sequence[ChessPiece | None]],
    origin: Coord,
    target: Coord,
) -> bool:
    """Return whether the origin piece attacks the target square."""

    row, col = int(origin[0]), int(origin[1])
    piece = board[row][col]
    if piece is None:
        return False
    if str(piece.kind) == "pawn":
        return tuple(target) in pawn_attack_squares(origin, str(piece.color))
    return tuple(target) in piece_move_destinations(board, origin, include_pawn_double_step=False)


def piece_capture_targets(board: Sequence[Sequence[ChessPiece | None]], coord: Coord) -> Tuple[Coord, ...]:
    """Return opponent-occupied squares capturable by one piece in a single move."""

    row, col = int(coord[0]), int(coord[1])
    piece = board[row][col]
    if piece is None:
        return ()
    captures = []
    for dest in piece_move_destinations(board, coord):
        occupant = board[int(dest[0])][int(dest[1])]
        if occupant is not None and str(occupant.color) != str(piece.color) and str(occupant.kind) != "king":
            captures.append((int(dest[0]), int(dest[1])))
    return tuple(captures)


def capturable_opponent_coords(board: Sequence[Sequence[ChessPiece | None]], player_color: str) -> Tuple[Coord, ...]:
    """Return unique opponent-piece squares capturable by the requested side."""

    captures: set[Coord] = set()
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None or str(piece.color) != str(player_color):
            continue
        captures.update(piece_capture_targets(board, coord))
    return tuple(sorted(captures))


def attackers_to_square(
    board: Sequence[Sequence[ChessPiece | None]],
    target: Coord,
    attacker_color: str,
) -> Tuple[Coord, ...]:
    """Return all pieces of one color attacking a target square."""

    attackers: List[Coord] = []
    for coord in occupied_coords(board):
        piece = board[int(coord[0])][int(coord[1])]
        if piece is None or str(piece.color) != str(attacker_color):
            continue
        if piece_attacks_square(board, coord, target):
            attackers.append((int(coord[0]), int(coord[1])))
    return tuple(sorted(attackers))


def king_escape_squares(board: Sequence[Sequence[ChessPiece | None]], king_coord: Coord) -> Tuple[Coord, ...]:
    """Return legal one-step king destinations that are not attacked after moving."""

    row, col = int(king_coord[0]), int(king_coord[1])
    piece = board[row][col]
    if piece is None or str(piece.kind) != "king":
        return ()
    escapes: List[Coord] = []
    for dest in piece_move_destinations(board, king_coord, include_pawn_double_step=False):
        dest_piece = board[int(dest[0])][int(dest[1])]
        if dest_piece is not None and str(dest_piece.kind) == "king":
            continue
        mutable = [list(board_row) for board_row in board]
        mutable[row][col] = None
        mutable[int(dest[0])][int(dest[1])] = piece
        moved_board = freeze_board(mutable)
        if not attackers_to_square(moved_board, dest, opponent(str(piece.color))):
            escapes.append((int(dest[0]), int(dest[1])))
    return tuple(sorted(escapes))


__all__ = [
    "BLACK",
    "BOARD_SIZE",
    "Board",
    "ChessPiece",
    "Coord",
    "NON_KING_PIECE_KINDS",
    "PIECE_KINDS",
    "WHITE",
    "attackers_to_square",
    "capturable_opponent_coords",
    "color_name",
    "coord_to_cell_id",
    "empty_board",
    "freeze_board",
    "in_bounds",
    "king_escape_squares",
    "occupied_coords",
    "occupied_piece_count",
    "opponent",
    "pawn_attack_squares",
    "piece_attacks_square",
    "piece_capture_targets",
    "piece_move_destinations",
    "piece_name",
    "piece_to_entity_id",
    "serialize_board",
]
