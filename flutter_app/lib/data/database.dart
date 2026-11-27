/// The journal of the user: a SQLite file of its own.
///
/// The file lives where the system of the device keeps the data of an
/// app: nothing leaves the machine and nothing is shared with anybody.
library;

import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import '../domain/rewards.dart';

/// The name of the file of the journal.
const String kDatabaseName = 'varagh.db';

/// The version of the shape of the file.
const int kDatabaseVersion = 1;

/// Open the journal of the user and make sure its shape is there.
Future<Database> openJournal({String? directory}) async {
  if (Platform.isWindows || Platform.isLinux || Platform.isMacOS) {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }
  String folder = directory ?? p.join((await getApplicationSupportDirectory()).path, 'varagh');
  await Directory(folder).create(recursive: true);
  return openDatabase(
    p.join(folder, kDatabaseName),
    version: kDatabaseVersion,
    onConfigure: (Database db) async {
      await db.execute('PRAGMA foreign_keys = ON');
    },
    onCreate: (Database db, int version) async {
      await _createShape(db);
    },
  );
}

/// The tables of the journal.
Future<void> _createShape(Database db) async {
  await db.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      notes TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'open',
      domain_id INTEGER,
      due_date TEXT,
      estimate_minutes INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      completed_at TEXT
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS learning_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      unit TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'active',
      progress TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      deleted_at TEXT
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      period_type TEXT NOT NULL,
      period_start TEXT NOT NULL,
      period_end TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'draft',
      stats TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS medals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      tier TEXT NOT NULL,
      virtue TEXT NOT NULL,
      kind TEXT NOT NULL DEFAULT 'earned',
      domain_id INTEGER,
      month_key TEXT NOT NULL,
      value_raw INTEGER NOT NULL DEFAULT 0,
      value_counted INTEGER NOT NULL DEFAULT 0,
      awarded_at TEXT NOT NULL
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS title_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title_key TEXT NOT NULL,
      reached_at TEXT NOT NULL
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )
  ''');
  await db.execute(
    'CREATE INDEX IF NOT EXISTS ix_medals_month_key ON medals (month_key)',
  );
}

/// The reading of the hall: the medals, the musters and the titles.
class HonoursSnapshot {
  const HonoursSnapshot({
    required this.medals,
    required this.musters,
    required this.reachedTitles,
  });

  final List<MedalRecord> medals;
  final int musters;
  final List<String> reachedTitles;

  /// Read the hall out of the journal.
  static Future<HonoursSnapshot> read(Database db) async {
    final List<Map<String, Object?>> medalRows = await db.query(
      'medals',
      columns: <String>['tier', 'virtue', 'value_counted', 'month_key'],
      orderBy: 'awarded_at ASC',
    );
    final List<MedalRecord> medals = medalRows
        .map(
          (Map<String, Object?> row) => MedalRecord(
            tier: row['tier']! as String,
            virtue: row['virtue']! as String,
            valueCounted: row['value_counted']! as int,
            monthKey: (row['month_key'] as String?) ?? '',
          ),
        )
        .toList();

    final List<Map<String, Object?>> reviewRows = await db.query(
      'reviews',
      columns: <String>['id'],
      where: "status = 'finished'",
    );
    final List<Map<String, Object?>> titleRows = await db.query(
      'title_history',
      columns: <String>['title_key'],
      orderBy: 'reached_at ASC',
    );

    return HonoursSnapshot(
      medals: medals,
      musters: reviewRows.length,
      reachedTitles: titleRows
          .map((Map<String, Object?> row) => row['title_key']! as String)
          .toList(),
    );
  }
}

/// Read a setting of the journal.
Future<String?> readSetting(Database db, String key) async {
  final List<Map<String, Object?>> rows = await db.query(
    'settings',
    columns: <String>['value'],
    where: 'key = ?',
    whereArgs: <Object?>[key],
    limit: 1,
  );
  if (rows.isEmpty) return null;
  return rows.first['value'] as String?;
}

/// Write a setting of the journal.
Future<void> writeSetting(Database db, String key, String value) async {
  await db.insert(
    'settings',
    <String, Object?>{'key': key, 'value': value},
    conflictAlgorithm: ConflictAlgorithm.replace,
  );
}
