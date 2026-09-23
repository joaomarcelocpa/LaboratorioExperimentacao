class Solution:
    def findLeastNumOfUniqueInts(self, arr: List[int], k: int) -> int:
        m = collections.defaultdict(int)

        for num in arr:
            m[num] += 1

        s = sorted(m.values())

        index = 0

        while k > 0 and index < len(s):
            if k >= s[index]:
                k -= s[index]
                index += 1
            else:
                break

        return len(s) - index