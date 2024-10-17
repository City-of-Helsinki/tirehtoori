from redirect.factories import UniqueFaker


def test_unique_faker():
    # Not a very deterministic test, but thanks to birthday paradox, it should
    # be very unlikely to give a false positive if the implementation is incorrect.
    faker_field = UniqueFaker("random_int")
    used_values = set()
    for _ in range(10000):
        # As of 2024-10-17, UniqueFaker (or, rather, faker.proxy.UniqueProxy) attempts
        # to generate a unique value up to 1000 times, so the random range is
        # intentionally set to a larger range than the number of iterations to reduce
        # the chance of false negatives.
        # The very final step actually has a very large chance of *not* being unique
        # (~91% since 9999 out of 11000 numbers are already in use), but since it's
        # repeated 1000 times, the chance of a false negative becomes virtually zero.
        value = faker_field.evaluate(
            None, None, {"locale": "en_US", "min": 1, "max": 11000}
        )
        assert value not in used_values
        used_values.add(value)
