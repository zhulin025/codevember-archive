import unittest

from collect import daily_updates, work_key


def work(day=5, title='Moss', **changes):
    return {'creator': 'artist', 'day': day, 'url': f'https://example.com/{day}/',
            'title': title, **changes}


class DailyUpdatesTests(unittest.TestCase):
    def updates(self, old, works, date='2026-11-18'):
        return daily_updates(old, {work_key(row): row for row in works}, date)

    def test_existing_catalogue_starts_without_false_updates(self):
        row = work()
        self.assertEqual(self.updates({'works': [row]}, [row]),
                         {'date': '2026-11-18', 'themes': []})

    def test_new_work_marks_its_theme(self):
        old = work()
        new = work(url='https://example.com/another-moss/')
        self.assertEqual(self.updates({'works': [old]}, [old, new])['themes'], ['05'])

    def test_same_day_batches_and_retries_keep_all_updates(self):
        row = work()
        old = {'works': [row], 'dailyUpdates': {'date': '2026-11-18', 'themes': ['05']}}
        self.assertEqual(self.updates(old, [row, work(12)])['themes'], ['05', '12'])
        self.assertEqual(self.updates(old, [row])['themes'], ['05'])

    def test_next_day_replaces_yesterdays_themes_even_without_additions(self):
        row = work()
        old = {'works': [row], 'dailyUpdates': {'date': '2026-11-17', 'themes': ['05']}}
        self.assertEqual(self.updates(old, [row, work(12)])['themes'], ['12'])
        self.assertEqual(self.updates(old, [row])['themes'], [])

    def test_title_and_cover_changes_do_not_count_as_new_work(self):
        row = work()
        self.assertEqual(self.updates({'works': [row]}, [
            {**row, 'title': 'Renamed', 'image': 'https://example.com/cover.jpg'}
        ])['themes'], [])

    def test_custom_themes_mark_the_custom_theme_row(self):
        row = {'creator': 'artist', 'theme': 'Silk', 'url': 'https://example.com/silk/'}
        self.assertEqual(self.updates({}, [row])['themes'], ['free'])


if __name__ == '__main__':
    unittest.main()
