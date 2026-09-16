class Solution:
    def finalValueAfterOperations(self, operations: list[str]) -> int:

        n = 0
        n_operations = len(operations)

        for i in range(n_operations):
            if operations[i] == "X++" or operations[i] == "++X":
                n = n + 1
            elif operations[i] == "X--" or operations[i] == "--X":
                n = n - 1

        return n