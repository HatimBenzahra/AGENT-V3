# Example of map and filter functions

# Define a list of numbers
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Use map to square each number
squared_numbers = list(map(lambda x: x**2, numbers))

# Use filter to keep only even numbers
even_numbers = list(filter(lambda x: x % 2 == 0, numbers))

# Print the results
print("Original numbers:", numbers)
print("Squared numbers:", squared_numbers)
print("Even numbers:", even_numbers)
