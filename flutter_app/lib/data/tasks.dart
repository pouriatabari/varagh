/// The tasks of the user: the reading and the writing of the journal.
library;

import 'package:sqflite/sqflite.dart';

/// A task of the user.
class Task {
  const Task({
    required this.id,
    required this.title,
    required this.descriptionMd,
    required this.status,
    required this.priority,
    required this.context,
    required this.domainId,
    required this.dueAt,
    required this.effortMinutes,
    required this.completedAt,
    required this.deletedAt,
    required this.countsForMedals,
  });

  final int id;
  final String title;
  final String descriptionMd;
  final String status;
  final int priority;
  final String context;
  final int? domainId;
  final String? dueAt;
  final int? effortMinutes;
  final String? completedAt;
  final String? deletedAt;
  final bool countsForMedals;

  /// The task is still open.
  bool get isOpen => status == 'todo' || status == 'doing';

  /// The task was finished.
  bool get isDone => status == 'done';

  /// Read a task out of a row of the journal.
  static Task fromRow(Map<String, Object?> row) {
    return Task(
      id: row['id']! as int,
      title: row['title'] as String? ?? '',
      descriptionMd: row['description_md'] as String? ?? '',
      status: row['status'] as String? ?? 'todo',
      priority: row['priority'] as int? ?? 2,
      context: row['context'] as String? ?? 'personal',
      domainId: row['domain_id'] as int?,
      dueAt: row['due_at'] as String?,
      effortMinutes: row['effort_minutes_estimate'] as int?,
      completedAt: row['completed_at'] as String?,
      deletedAt: row['deleted_at'] as String?,
      countsForMedals: (row['counts_for_medals'] as int? ?? 1) == 1,
    );
  }
}

/// The reading and the writing of the tasks.
class TaskRepository {
  const TaskRepository(this.db);

  final Database db;

  /// The tasks of the user, the open ones first.
  Future<List<Task>> list({bool onlyOpen = false, String search = ''}) async {
    final List<String> where = <String>['deleted_at IS NULL'];
    final List<Object?> args = <Object?>[];
    if (onlyOpen) {
      where.add("status IN ('todo', 'doing')");
    }
    if (search.isNotEmpty) {
      where.add('(title LIKE ? OR description_md LIKE ?)');
      args.addAll(<Object?>['%$search%', '%$search%']);
    }
    final List<Map<String, Object?>> rows = await db.query(
      'tasks',
      where: where.join(' AND '),
      whereArgs: args,
      orderBy: "CASE status WHEN 'doing' THEN 0 WHEN 'todo' THEN 1 ELSE 2 END, "
          "COALESCE(due_at, '9999') ASC, created_at DESC",
    );
    return rows.map(Task.fromRow).toList();
  }

  /// Write a new task and give back its number.
  Future<int> create({
    required String title,
    String descriptionMd = '',
    String context = 'personal',
    int priority = 2,
    int? domainId,
    String? dueAt,
    int? effortMinutes,
    bool countsForMedals = true,
  }) async {
    final String now = DateTime.now().toUtc().toIso8601String();
    return db.insert('tasks', <String, Object?>{
      'title': title,
      'description_md': descriptionMd,
      'status': 'todo',
      'priority': priority,
      'origin': 'self_initiated',
      'context': context,
      'domain_id': domainId,
      'due_at': dueAt,
      'effort_minutes_estimate': effortMinutes,
      'counts_for_medals': countsForMedals ? 1 : 0,
      'created_at': now,
    });
  }

  /// Change a task.
  Future<void> update(Task task, {String? title, String? descriptionMd}) async {
    await db.update(
      'tasks',
      <String, Object?>{
        if (title != null) 'title': title,
        if (descriptionMd != null) 'description_md': descriptionMd,
        'last_activity_at': DateTime.now().toUtc().toIso8601String(),
      },
      where: 'id = ?',
      whereArgs: <Object?>[task.id],
    );
  }

  /// Start a task, or stop it.
  Future<void> setStatus(int id, String status) async {
    final String now = DateTime.now().toUtc().toIso8601String();
    await db.update(
      'tasks',
      <String, Object?>{
        'status': status,
        'started_at': status == 'doing' ? now : null,
        'completed_at': status == 'done' ? now : null,
        'last_activity_at': now,
      },
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
  }

  /// Hide a task without throwing it away.
  Future<void> softDelete(int id) async {
    await db.update(
      'tasks',
      <String, Object?>{
        'deleted_at': DateTime.now().toUtc().toIso8601String(),
      },
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
  }

  /// The number of the tasks that are open.
  Future<int> countOpen() async {
    final List<Map<String, Object?>> rows = await db.rawQuery(
      "SELECT COUNT(*) AS total FROM tasks "
      "WHERE deleted_at IS NULL AND status IN ('todo', 'doing')",
    );
    return (rows.first['total'] as int?) ?? 0;
  }
}

/// The domains of the user: the areas the work is sorted into.
class DomainRepository {
  const DomainRepository(this.db);

  final Database db;

  /// The domains of the user.
  Future<List<Map<String, Object?>>> list() async {
    return db.query('domains', orderBy: 'name COLLATE NOCASE ASC');
  }

  /// Write a domain.
  Future<int> create(String name) async {
    return db.insert('domains', <String, Object?>{
      'name': name,
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
  }
}
