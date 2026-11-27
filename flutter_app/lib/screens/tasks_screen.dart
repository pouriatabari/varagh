/// The list of the tasks of the user.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../i18n.dart';

/// The tasks: the open ones and the ones that were done.
class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key, required this.database});

  final Database database;

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  List<Map<String, Object?>> _tasks = <Map<String, Object?>>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<Map<String, Object?>> rows = await widget.database.query(
      'tasks',
      orderBy: 'created_at DESC',
      limit: 200,
    );
    if (!mounted) return;
    setState(() => _tasks = rows);
  }

  @override
  Widget build(BuildContext context) {
    if (_tasks.isEmpty) {
      return Center(child: Text(Fa.t('nav.tasks')));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: _tasks.length,
      separatorBuilder: (BuildContext context, int index) => const Divider(height: 1),
      itemBuilder: (BuildContext context, int index) {
        final Map<String, Object?> task = _tasks[index];
        return ListTile(
          title: Text('${task['title'] ?? ''}'),
          subtitle: Text('${task['status'] ?? ''}'),
        );
      },
    );
  }
}
