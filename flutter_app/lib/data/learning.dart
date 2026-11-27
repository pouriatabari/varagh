/// The learning: the items of the syllabus and how far they came.
library;

import 'package:sqflite/sqflite.dart';

/// One item of the learning.
class LearningItem {
  const LearningItem({
    required this.id,
    required this.title,
    required this.unit,
    required this.status,
    required this.progress,
  });

  final int id;
  final String title;
  final String unit;
  final String status;
  final String progress;

  /// Read an item out of a row of the journal.
  static LearningItem fromRow(Map<String, Object?> row) {
    return LearningItem(
      id: row['id']! as int,
      title: row['title'] as String? ?? '',
      unit: row['unit'] as String? ?? '',
      status: row['status'] as String? ?? 'active',
      progress: row['progress'] as String? ?? '',
    );
  }
}

/// The reading and the writing of the learning items.
class LearningRepository {
  const LearningRepository(this.db);

  final Database db;

  /// The items of the user.
  Future<List<LearningItem>> list({bool onlyActive = false}) async {
    final List<Map<String, Object?>> rows = await db.query(
      'learning_items',
      where: onlyActive
          ? "deleted_at IS NULL AND status = 'active'"
          : 'deleted_at IS NULL',
      orderBy: 'created_at DESC',
      limit: 200,
    );
    return rows.map(LearningItem.fromRow).toList();
  }

  /// Write an item.
  Future<int> create({
    required String title,
    String unit = '',
    String status = 'active',
    String progress = '',
  }) async {
    return db.insert('learning_items', <String, Object?>{
      'title': title,
      'unit': unit,
      'status': status,
      'progress': progress,
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
  }

  /// Change an item.
  Future<void> update(
    int id, {
    String? title,
    String? unit,
    String? status,
    String? progress,
  }) async {
    await db.update(
      'learning_items',
      <String, Object?>{
        if (title != null) 'title': title,
        if (unit != null) 'unit': unit,
        if (status != null) 'status': status,
        if (progress != null) 'progress': progress,
      },
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
  }

  /// Hide an item without throwing it away.
  Future<void> softDelete(int id) async {
    await db.update(
      'learning_items',
      <String, Object?>{
        'deleted_at': DateTime.now().toUtc().toIso8601String(),
      },
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
  }
}
