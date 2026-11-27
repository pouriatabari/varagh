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
DateTime gregorianOf(int jy, int jm, int jd) {
  int gy;
  int adjusted = jy;
  if (jy > 979) {
    gy = 1600;
    adjusted = jy - 979;
  } else {
    gy = kJalaliEpoch;
  }

  int days = 365 * adjusted +
      (adjusted ~/ 33) * 8 +
      (((adjusted % 33) + 3) ~/ 4) +
      78 +
      jd +
      (jm < 7 ? (jm - 1) * 31 : ((jm - 7) * 30) + 186);

  gy += 400 * (days ~/ 146097);
  days %= 146097;
  if (days > 36524) {
    gy += 100 * (days ~/ 36524);
    days %= 36524;
    if (days >= 365) days += 1;
  }
  gy += 4 * (days ~/ 1461);
  days %= 1461;
  if (days > 365) {
    gy += (days - 1) ~/ 365;
    days = (days - 1) % 365;
  }
  int gd = days + 1;

  final List<int> lengthOfMonth = <int>[
    0,
    31,
    _isGregorianLeap(gy) ? 29 : 28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
  ];
  int gm = 0;
  while (gm < 13 && gd > lengthOfMonth[gm]) {
    gd -= lengthOfMonth[gm];
    gm += 1;
  }
  return DateTime(gy, gm, gd);
}

/// The Gregorian year has a leap day.
bool _isGregorianLeap(int year) =>
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;

/// The Persian year has a leap day.
bool isLeapJalali(int year) {
  final int remainder = year % 33;
  return remainder == 1 || remainder == 5 || remainder == 9 || remainder == 13 ||
      remainder == 17 || remainder == 22 || remainder == 26 || remainder == 30;
}

/// The number of the days of a month of the Persian calendar.
int daysInJalaliMonth(int year, int month) {
  if (month <= 6) return 31;
  if (month <= 11) return 30;
  return isLeapJalali(year) ? 30 : 29;
}

/// The month of a date, the way the medals are counted: 1404/01.
String monthKeyOf(DateTime value) => jalaliOf(value).monthKey;

/// The date of a month of the Persian calendar, the first day of it.
DateTime firstOfJalaliMonth(int year, int month) => gregorianOf(year, month, 1);
