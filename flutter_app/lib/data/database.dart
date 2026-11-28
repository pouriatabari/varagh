/// The journal of the user: a SQLite file of its own.
///
/// The file lives where the system of the device keeps the data of an
/// app: nothing leaves the machine and nothing is shared with anybody.
library;

import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../domain/rewards.dart';
import 'desktop_factory_stub.dart'
    if (dart.library.io) 'desktop_factory_io.dart';

export 'package:sqflite/sqflite.dart' show Database;

/// The name of the file of the journal.
const String kDatabaseName = 'varagh.db';

/// The version of the shape of the file.
const int kDatabaseVersion = 1;

/// Open the journal of the user and make sure its shape is there.
Future<Database> openJournal({String? directory}) async {
  prepareDatabaseFactory();
  final String folder =
      directory ?? p.join((await getApplicationSupportDirectory()).path, 'varagh');
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
      description_md TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'todo',
      priority INTEGER NOT NULL DEFAULT 2,
      origin TEXT NOT NULL DEFAULT 'self_initiated',
      context TEXT NOT NULL DEFAULT 'personal',
      domain_id INTEGER,
      due_at TEXT,
      effort_minutes_estimate INTEGER,
      started_at TEXT,
      completed_at TEXT,
      last_activity_at TEXT,
      deleted_at TEXT,
      is_private INTEGER NOT NULL DEFAULT 1,
      counts_for_medals INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS domains (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      color TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL
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
    CREATE TABLE IF NOT EXISTS medal_proposals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      review_id INTEGER,
      title TEXT NOT NULL,
      tier TEXT NOT NULL,
      virtue TEXT NOT NULL DEFAULT 'prowess',
      evidence_task_ids TEXT NOT NULL DEFAULT '[]',
      impact_note INTEGER NOT NULL DEFAULT 0,
      concrete INTEGER NOT NULL DEFAULT 0,
      domain_name TEXT
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS medal_evidence (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      medal_id INTEGER NOT NULL,
      task_id INTEGER NOT NULL,
      UNIQUE (task_id)
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
  await db.execute('''
    CREATE TABLE IF NOT EXISTS realm_claims (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      realm_key TEXT NOT NULL UNIQUE,
      domain_id INTEGER,
      domain_name TEXT,
      assigned_at TEXT NOT NULL,
      claimed_at TEXT
    )
  ''');
  await db.execute('''
    CREATE TABLE IF NOT EXISTS journal_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date_key TEXT NOT NULL,
      text TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
  ''');
  await db.execute(
    'CREATE INDEX IF NOT EXISTS ix_journal_date ON journal_entries (date_key)',
  );
  await db.execute('''
    CREATE TABLE IF NOT EXISTS time_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      kind TEXT NOT NULL DEFAULT 'work',
      task_id INTEGER,
      learning_item_id INTEGER,
      started_at TEXT NOT NULL,
      ended_at TEXT,
      duration_minutes INTEGER NOT NULL DEFAULT 0,
      reason TEXT NOT NULL DEFAULT '',
      note TEXT NOT NULL DEFAULT ''
    )
  ''');
  await db.execute(
    'CREATE INDEX IF NOT EXISTS ix_time_started_at ON time_entries (started_at)',
  );
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
