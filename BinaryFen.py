import chess


# 12 => theres an ep square behind the pawn, rank will be deduced from the rank
# 13 => any white rook with castling rights, side will be deduced from the file
# 14 => any black rook with castling rights, side will be deduced from the file
# 15 => black king and black is side to move
def convert_meaning(board: chess.Board, sq: chess.Square, piece: chess.Piece) -> int:
    if piece.piece_type == chess.PAWN and sq ^ 8 == board.ep_square:
        return 12

    if piece.piece_type == chess.ROOK:
        if board.castling_rights & chess.BB_SQUARES[sq]:
            if piece.color == chess.WHITE:
                return 13

            if piece.color == chess.BLACK:
                return 14

    if piece.piece_type == chess.KING and piece.color == chess.BLACK and board.turn == chess.BLACK:
        return 15

    return piece.piece_type + (-1 if piece.color == chess.WHITE else 5)


def encode(board: chess.Board) -> bytes:
    packed = bytearray(24)

    packed[0] = board.occupied >> 56
    packed[1] = (board.occupied >> 48) & 0xFF
    packed[2] = (board.occupied >> 40) & 0xFF
    packed[3] = (board.occupied >> 32) & 0xFF
    packed[4] = (board.occupied >> 24) & 0xFF
    packed[5] = (board.occupied >> 16) & 0xFF
    packed[6] = (board.occupied >> 8) & 0xFF
    packed[7] = board.occupied & 0xFF

    offset = 16

    for sq, piece in reversed(board.piece_map().items()):
        # it is faster to reverse the piece_map than to use scan_forward().
        # we now fill the packed array, since our convertedpiece only actually needs 4 bits,
        # we can store 2 pieces in one byte.
        shift = 4 if offset % 2 == 0 else 0
        packed[offset // 2] |= convert_meaning(board, sq, piece) << shift
        offset += 1

    return bytes(packed)


# for pieces with a special meaning return None
def convert_piece(piece: int) -> chess.Piece | None:
    if piece >= 12:
        return

    if piece <= 5:
        return chess.Piece(piece + 1, chess.WHITE)

    return chess.Piece(piece - 5, chess.BLACK)


def decode(compressed: bytes) -> chess.Board:
    occupied = 0

    for i in range(8):
        occupied |= compressed[i] << (56 - i * 8)

    offset = 16

    # get an empty board
    board = chess.Board.empty()

    # place pieces back on the board
    while occupied:
        sq = chess.lsb(occupied)
        occupied &= occupied - 1
        nibble = compressed[offset // 2] >> (4 if offset % 2 == 0 else 0) & 0b1111
        piece = convert_piece(nibble)

        if piece is not None:
            board.set_piece_at(sq, piece)
            offset += 1
            continue

        # Piece has a special meaning, interpret it from the raw integer
        # pawn with ep square behind it
        if nibble == 12:
            board.ep_square = sq ^ 8

            color = chess.WHITE if chess.square_rank(sq) == 3 else chess.BLACK
            board.set_piece_at(sq, chess.Piece(chess.PAWN, color))

        # castling rights for white
        elif nibble == 13:
            board.castling_rights |= chess.BB_SQUARES[sq]
            board.set_piece_at(sq, chess.Piece(chess.ROOK, chess.WHITE))

        # castling rights for black
        elif nibble == 14:
            board.castling_rights |= chess.BB_SQUARES[sq]
            board.set_piece_at(sq, chess.Piece(chess.ROOK, chess.BLACK))

        # black to move king
        elif nibble == 15:
            board.turn = chess.BLACK
            board.set_piece_at(sq, chess.Piece(chess.KING, chess.BLACK))

        offset += 1

    return board
