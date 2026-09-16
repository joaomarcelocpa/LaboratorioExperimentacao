class Solution:
    def tictactoe(self, moves: List[List[int]]) -> str:
        n = 3

        rows = [0] * n
        cols = [0] * n

        diagonal1 = 0
        diagonal2 = 0

        player = 1

        for r, c in moves:
            rows[r] += player
            cols[c] += player

            if r == c:
                diagonal1 += player

            if r + c == n - 1:
                diagonal2 += player

            if (
                abs(rows[r]) == n
                or abs(cols[c]) == n
                or abs(diagonal1) == n
                or abs(diagonal2) == n
            ):
                return "A" if player == 1 else "B"

            player *= -1

        if len(moves) == n * n:
            return "Draw"

        return "Pending"