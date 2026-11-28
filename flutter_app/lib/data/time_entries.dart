/// The measured time: the blocks of time the user has worked.
library;

import 'package:sqflite/sqflite.dart';

import '../utils/jalali.dart';

/// The kinds of a measured block.
const List<String> kTimeKinds = <String>['work', 'overtime', 'study', 'learning'];

/// A measured block of time.
class TimeEntry {
  const TimeEntry({
    required this.id,
    required this.kind,
    required this.startedAt,
    required this.endedAt,
    required this.durationMinutes,
    required this.taskId,
    required this.note,
    required this.reason,
  });

  final int id;
  final String kind;
  final DateTime startedAt;
  final DateTime? endedAt;
  final int? durationMinutes;
  final int? taskId;
  final String note;
  final String reason;

  static TimeEntry fromRow(Map<String, Object?> row) {
    return TimeEntry(
      id: row['id']! as int,
      kind: row['kind'] as String? ?? 'work',
      startedAt: DateTime.parse(row['started_at']! as String).toLocal(),
      endedAt: row['ended_at'] == null
          ? null
          : DateTime.parse(row['ended_at']! as String).toLocal(),
      durationMinutes: row['duration_minutes'] as int?,
      taskId: row['task_id'] as int?,
      note: row['note'] as String? ?? '',
      reason: row['reason'] as String? ?? '',
    );
  }
}

/// The reading and the writing of the measured time.
class TimeRepository {
  const TimeRepository(this.db);

  final Database db;

  /// The blocks of the user, the newest first.
  Future<List<TimeEntry>> list({int limit = 200}) async {
    final List<Map<String, Object?>> rows = await db.query(
      'time_entries',
      orderBy: 'started_at DESC',
      limit: limit,
    );
    return rows.map(TimeEntry.fromRow).toList();
  }

  /// The blocks of one day, in the Persian calendar.
  Future<List<TimeEntry>> listOfDay(DateTime day) async {
    final String key = jalaliOf(day).plain;
    final List<Map<String, Object?>> rows = await db.query(
      'time_entries',
      where: "substr(started_at, 1, 10) >= ? AND substr(started_at, 1, 10) <= ?",
      whereArgs: <Object?>[
        '${_gregorianOf(key)}T00:00:00',
        '${_gregorianOf(key)}T23:59:59',
      ],
      orderBy: 'started_at DESC',
    );
    return rows.map(TimeEntry.fromRow).toList();
  }

  /// Start a block of time.
  Future<int> start({
    String kind = 'work',
    int? taskId,
    int? learningItemId,
    DateTime? at,
  }) async {
    final DateTime started = (at ?? DateTime.now()).toUtc();
    return db.insert('time_entries', <String, Object?>{
      'kind': kind,
      'task_id': taskId,
      'learning_item_id': learningItemId,
      'started_at': started.toIso8601String(),
      'duration_minutes': 0,
    });
  }

  /// Close a block of time.
  Future<void> stop(int id, {DateTime? at}) async {
    final DateTime ended = (at ?? DateTime.now()).toUtc();
    final List<Map<String, Object?>> rows = await db.query(
      'time_entries',
      columns: <String>['started_at'],
      where: 'id = ?',
      whereArgs: <Object?>[id],
      limit: 1,
    );
    if (rows.isEmpty) return;
    final DateTime started = DateTime.parse(rows.first['started_at']! as String);
    final int minutes = ended.difference(started).inMinutes;
    await db.update(
      'time_entries',
      <String, Object?>{
        'ended_at': ended.toIso8601String(),
        'duration_minutes': minutes < 0 ? 0 : minutes,
      },
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
  }

  /// The number of the minutes of a kind, over the blocks that were given.
  Future<int> minutesOfKind(String kind) async {
    final List<Map<String, Object?>> rows = await db.rawQuery(
      'SELECT COALESCE(SUM(duration_minutes), 0) AS total FROM time_entries '
      'WHERE kind = ? AND duration_minutes IS NOT NULL',
      <Object?>[kind],
    );
    return (rows.first['total'] as int?) ?? 0;
  }

  /// The number of the minutes of the work of today.
  Future<int> minutesToday() async {
    final List<TimeEntry> entries = await listOfDay(DateTime.now());
    int total = 0;
    for (final TimeEntry entry in entries) {
      if (entry.kind == 'overtime') continue;
      total += entry.durationMinutes ?? 0;
    }
    return total;
  }

  /// The day of a Persian key, as a Gregorian date.
  String _gregorianOf(String key) {
    final List<String> parts = key.split('/');
    final DateTime day = gregorianOf(
      int.parse(parts[0]),
      int.parse(parts[1]),
      int.parse(parts[2]),
    );
    final String month = day.month.toString().padLeft(2, '0');
    final String date = day.day.toString().padLeft(2, '0');
    return '${day.year}-$month-$date';
  }
}
