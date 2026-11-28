/// The Jalali (Shamsi) calendar, in Dart.
///
/// The journal stores the Gregorian time in UTC; the Persian calendar is
/// only ever a way of writing a date down for the user. The conversion is
/// the one of the Borkowski algorithm, the same one the python app uses.
library;

/// A date of the Persian calendar.
class JalaliDate {
  const JalaliDate(this.year, this.month, this.day);

  final int year;
  final int month;
  final int day;

  /// The date as it is written for the user: ۱۴۰۴/۰۱/۰۵.
  String get short => '${_pad(year)}/${_pad(month)}/${_pad(day)}';

  /// The date as it is written in the journal: 1404/01/05.
  String get plain => '$year/${_pad(month)}/${_pad(day)}';

  /// The month of the medal: 1404/01.
  String get monthKey => '$year/${_pad(month)}';

  /// The date in the Persian numbers.
  String get persian => '${_fa(year)}/${_fa(month)}/${_fa(day)}';

  @override
  String toString() => plain;

  static String _pad(int value) => value.toString().padLeft(2, '0');

  static String _fa(int value) {
    const List<String> digits = <String>['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'];
    return value.toString().split('').map((String d) => digits[int.parse(d)]).join();
  }
}

/// The names of the months of the Persian calendar.
const List<String> kPersianMonths = <String>[
  'فروردین',
  'اردیبهشت',
  'خرداد',
  'تیر',
  'مرداد',
  'شهریور',
  'مهر',
  'آبان',
  'آذر',
  'دی',
  'بهمن',
  'اسفند',
];

/// The names of the days of the week, Saturday first.
const List<String> kPersianWeekdays = <String>[
  'شنبه',
  'یکشنبه',
  'دوشنبه',
  'سه‌شنبه',
  'چهارشنبه',
  'پنجشنبه',
  'جمعه',
];

/// The Gregorian year the Jalali year started from.
const int kJalaliEpoch = 621;

/// Convert a Gregorian date into a Jalali date.
JalaliDate jalaliOf(DateTime value) {
  final int gy = value.year;
  final int gm = value.month;
  final int gd = value.day;

  const List<int> daysOfMonth = <int>[0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

  int jy = gy > 1600 ? 979 : 0;
  final int adjusted = gy > 1600 ? gy - 1600 : gy - kJalaliEpoch;
  final int gy2 = gm > 2 ? adjusted + 1 : adjusted;

  int days = 365 * adjusted +
      ((gy2 + 3) ~/ 4) -
      ((gy2 + 99) ~/ 100) +
      ((gy2 + 399) ~/ 400) -
      80 +
      gd +
      daysOfMonth[gm - 1];

  jy += 33 * (days ~/ 12053);
  days %= 12053;
  jy += 4 * (days ~/ 1461);
  days %= 1461;
  if (days > 365) {
    jy += (days - 1) ~/ 365;
    days = (days - 1) % 365;
  }

  int jm;
  int jd;
  if (days < 186) {
    jm = 1 + days ~/ 31;
    jd = 1 + days % 31;
  } else {
    jm = 7 + (days - 186) ~/ 30;
    jd = 1 + (days - 186) % 30;
  }
  return JalaliDate(jy, jm, jd);
}

/// Convert a Jalali date into a Gregorian date.
///
/// The first day of the Persian year is found with the conversion above,
/// and the day of the year is added to it, so the two directions can never
/// disagree about the length of a year.
DateTime gregorianOf(int jy, int jm, int jd) {
  final DateTime start = _startOfJalaliYear(jy);
  return start.add(Duration(days: _dayOfJalaliYear(jy, jm, jd) - 1));
}

/// The first day of a Persian year, as a Gregorian date.
DateTime _startOfJalaliYear(int jy) {
  final DateTime guess = DateTime(jy + 621, 3, 21);
  for (int shift = -3; shift <= 3; shift++) {
    final DateTime day = guess.add(Duration(days: shift));
    final JalaliDate jalali = jalaliOf(day);
    if (jalali.year == jy && jalali.month == 1 && jalali.day == 1) return day;
  }
  return guess;
}

/// The day of the Persian year, the first of Farvardin being the first.
int _dayOfJalaliYear(int jy, int jm, int jd) {
  int day = jd;
  for (int month = 1; month < jm; month++) {
    day += _lengthOfJalaliMonth(jy, month);
  }
  return day;
}

/// The number of the days of a month of the Persian calendar.
int _lengthOfJalaliMonth(int jy, int jm) {
  if (jm <= 6) return 31;
  if (jm <= 11) return 30;
  return _lengthOfJalaliYear(jy) - 336;
}

/// The number of the days of a Persian year.
int _lengthOfJalaliYear(int jy) =>
    _startOfJalaliYear(jy + 1).difference(_startOfJalaliYear(jy)).inDays;

/// The Persian year has a leap day.
bool isLeapJalali(int year) => _lengthOfJalaliYear(year) == 366;

/// The number of the days of a month of the Persian calendar.
int daysInJalaliMonth(int year, int month) => _lengthOfJalaliMonth(year, month);

/// The month of a date, the way the medals are counted: 1404/01.
String monthKeyOf(DateTime value) => jalaliOf(value).monthKey;

/// The date of a month of the Persian calendar, the first day of it.
DateTime firstOfJalaliMonth(int year, int month) => gregorianOf(year, month, 1);
