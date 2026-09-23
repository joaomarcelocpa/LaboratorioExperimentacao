class Solution:
    def constructMaximumBinaryTree(self, nums):
        return self.build(nums, 0, len(nums) - 1)

    def build(self, nums, esquerda, direita):
        if esquerda > direita:
            return None

        maior = esquerda
        for i in range(esquerda + 1, direita + 1):
            if nums[i] > nums[maior]:
                maior = i

        node = TreeNode(nums[maior])
        node.left = self.build(nums, esquerda, maior - 1)
        node.right = self.build(nums, maior + 1, direita)

        return node