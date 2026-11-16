"""Fixed public probe set, version 0.1.0."""
import re

PROBES = [('arith-1', 'What is 847 × 293? Reply with only the number.', 'exact', '248171'), ('arith-2', 'What is 17 + 25 × 4? Reply with only the number.', 'exact', '117'), ('capital-1', 'What is the capital of Australia? Reply with only the city name.', 'exact', 'Canberra'), ('capital-2', 'What is the capital of Canada? Reply with only the city name.', 'exact', 'Ottawa'), ('exact-word', 'Reply with exactly the word BLUE and nothing else.', 'exact', 'BLUE'), ('primes', 'List the first five prime numbers, separated by commas, and nothing else.', 'set', '2 3 5 7 11'), ('translate', "Translate 'good morning' to French. Reply with only the translation.", 'contains', 'bonjour'), ('reverse', "Reverse the string 'abcde'. Reply with only the reversed string.", 'exact', 'edcba'), ('count-letters', "How many times does the letter 's' appear in the word 'mississippi'? Reply with only the number.", 'exact', '4'), ('logic-1', 'A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. How much does the ball cost in cents? Reply with only the number.', 'exact', '5'), ('contains-words', 'Write one sentence that contains all three words: river, bridge, moon. Reply with only the sentence.', 'contains', 'river bridge moon'), ('identity', 'Which model are you? Reply in one short sentence.', 'none', '')]

def normalize(value):
    return " ".join(value.split()).casefold()

def check(probe, response):
    _, _, kind, expected = probe
    actual, expected = normalize(response), normalize(expected)
    if kind == "none":
        return None
    if kind == "exact":
        return actual == expected
    if kind == "set":
        return set(re.split(r"[,\s]+", actual.strip(", "))) == set(expected.split())
    return all(word in actual for word in expected.split())
