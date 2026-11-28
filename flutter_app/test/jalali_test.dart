/// The Persian calendar, checked against the dates the python app writes.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:varagh/utils/jalali.dart';

void main() {
  group('the conversion to the Persian calendar', () {
    test('the known days are the days they are', () {
      final Map<String, String> known = <String, String>{
        '2026-11-28': '1405/09/07',
        '2024-03-20': '1403/01/01',
        '2024-03-21': '1403/01/02',
        '2025-01-01': '1403/10/12',
        '2000-01-01': '1378/10/11',
        '1979-02-11': '1357/11/22',
      };
      known.forEach((String gregorian, String jalali) {
        final JalaliDate date = jalaliOf(DateTime.parse(gregorian));
        expect(date.plain, jalali, reason: gregorian);
      });
    });

    test('the month of a medal is the Persian month', () {
      expect(monthKeyOf(DateTime.parse('2026-11-28')), '1405/09');
      expect(monthKeyOf(DateTime.parse('2024-03-20')), '1403/01');
    });
  });

  group('the conversion to the Gregorian calendar', () {
    test('the way back is the way it came', () {
      final Map<String, String> known = <String, String>{
        '2026-11-28': '1405/09/07',
        '2024-03-20': '1403/01/01',
        '2025-01-01': '1403/10/12',
        '2000-01-01': '1378/10/11',
        '1979-02-11': '1357/11/22',
      };
      known.forEach((String gregorian, String jalali) {
        final List<String> parts = jalali.split('/');
        final DateTime back = gregorianOf(
          int.parse(parts[0]),
          int.parse(parts[1]),
          int.parse(parts[2]),
        );
        expect(
          '${back.year}-${back.month.toString().padLeft(2, '0')}-'
          '${back.day.toString().padLeft(2, '0')}',
          gregorian,
        );
      });
    });

    test('the length of the year is the length it is', () {
      expect(daysInJalaliMonth(1403, 1), 31);
      expect(daysInJalaliMonth(1403, 7), 30);
      expect(daysInJalaliMonth(1403, 12), 30);
      expect(daysInJalaliMonth(1404, 12), 29);
      expect(isLeapJalali(1403), isTrue);
      expect(isLeapJalali(1404), isFalse);
    });
  });
}
