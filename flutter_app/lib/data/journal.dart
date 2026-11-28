/// The journal of the user: a note for every day, a few notes for the
/// longer days.
library;

import 'package:sqflite/sqflite.dart';

/// A note of the journal.
class JournalEntry {
  const JournalEntry({
    required this.id,
    required this.dateKey,
    required this.text,
    required this.createdAt,
  });

  final int id;

  /// The day of the note in the Persian calendar (1404/09/07).
  final String dateKey;
  final String text;
  final String createdAt;

  static JournalEntry fromRow(Map<String, Object?> row) {
    return JournalEntry(
      id: row['id']! as int,
      dateKey: row['date_key'] as String? ?? '',
      text: row['text'] as String? ?? '',
      createdAt: row['created_at'] as String? ?? '',
    );
  }
}

/// The journal of the user.
class JournalRepository {
  const JournalRepository(this.db);

  final Database db;

  /// The notes of the user.
  Future<List<JournalEntry>> list({String? dateKey}) async {
    final List<Map<String, Object?>> rows = await db.query(
      'journal_entries',
      where: dateKey != null ? 'date_key = ?' : null,
      whereArgs: dateKey != null ? <Object?>[dateKey] : null,
      orderBy: 'created_at DESC',
      limit: 200,
    );
    return rows.map(JournalEntry.fromRow).toList();
  }

  /// Write a note.
  Future<int> create({required String dateKey, required String text}) async {
    return db.insert('journal_entries', <String, Object?>{
      'date_key': dateKey,
      'text': text,
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
  }

  /// Throw a note away.
  Future<void> delete(int id) async {
    await db.delete('journal_entries', where: 'id = ?', whereArgs: <Object?>[id]);
  }
}
