import random

# 1. Create a list of 10 random numbers between 1 and 20.
rand_list = [random.randint(1, 20) for _ in range(10)]
print("List of randomized numbers:", rand_list)

# 2. Filter Numbers Below 10 (List Comprehension)
below_10_lc = [n for n in rand_list if n < 10]
print("Numbers below 10 (list comprehension):", below_10_lc)

# 3. Filter Numbers Below 10 (Using filter)
below_10_filter = list(filter(lambda x: x < 10, rand_list))
print("Numbers below 10 (filter):", below_10_filter)