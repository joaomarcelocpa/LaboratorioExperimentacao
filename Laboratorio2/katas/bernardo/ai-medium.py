class Solution:
    def isAdditiveNumber(self, num: str) -> bool:
        n = len(num)
        
        def is_valid(x: str) -> bool:
            return x == "0" or x[0] != "0"
        
        def backtrack(first: str, second: str, rest: str) -> bool:
            if not rest:
                return True
            s = int(first) + int(second)
            s_str = str(s)
            if not rest.startswith(s_str):
                return False
            return backtrack(second, s_str, rest[len(s_str):])
        
        for i in range(1, n):
            first = num[:i]
            if not is_valid(first):
                break
            for j in range(i + 1, n):
                second = num[i:j]
                if not is_valid(second):
                    break
                if backtrack(first, second, num[j:]):
                    return True
        
        return False