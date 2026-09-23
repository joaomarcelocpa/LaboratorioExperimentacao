from collections import Counter


class Solution(object):
    def findLeastNumOfUniqueInts(self, arr, k):
        count = Counter(arr)
        freqs = sorted(count.values())

        unique_remaining = len(freqs)

        for f in freqs:
            if k >= f:
                k -= f
                unique_remaining -= 1
            else:
                break

        return unique_remaining