import re

def extract_numbers(text: str):
    # Refined regular expression to capture positive numbers after ':' and at the end of the line
    pattern = re.compile(r'box density avg over 20 samples:\s*([\d.]+(?:[eE][+-]?\d+)?)\s.*?\s([\d.]+(?:[eE][+-]?\d+)?)')
    matches = pattern.findall(text)
    return matches

# Sample text
text1 = "box density avg over 20 samples: 1.13 +. 0.01"
text2 = "box density avg over 20 samples: 4.40E+21 + 1.43E+20"

# Extract numbers
numbers1 = extract_numbers(text1)
numbers2 = extract_numbers(text2)

print(f"Extracted numbers from text1: {numbers1}")
print(f"Extracted numbers from text2: {numbers2}")

import pytest


def test_extract_numbers():
    # Sample texts
    text1 = "box density avg over 20 samples: 1.13 +. 0.01"
    text2 = "box density avg over 20 samples: 4.40E+21 + 1.43E+20"

    # Expected results
    expected1 = [('1.13', '0.01')]
    expected2 = [('4.40E+21', '1.43E+20')]

    # Run the function
    result1 = extract_numbers(text1)
    result2 = extract_numbers(text2)

    # Assert the results
    assert result1 == expected1
    assert result2 == expected2

if __name__ == "__main__":
    pytest.main()