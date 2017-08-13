import unittest

from iceburg.web.views import get_readable_duration


class HowLongNowTestCase(unittest.TestCase):
    def test_basic_duration(self):
        self.assertEqual(get_readable_duration(cost=100, net_per_year=100), 'in a year')
        self.assertEqual(get_readable_duration(cost=10, net_per_year=100), 'in a month')
        self.assertEqual(get_readable_duration(cost=50, net_per_year=100), 'in 6 months')
        self.assertEqual(get_readable_duration(cost=1, net_per_year=100), 'in 2 days')



if __name__ == '__main__':
    unittest.main()
