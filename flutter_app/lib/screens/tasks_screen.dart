/// The list of the tasks of the user.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/tasks.dart';
import '../i18n.dart';
import '../widgets/selection_list.dart';

/// The tasks: the open ones and the ones that were done.
class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key, required this.database});

  final Database database;

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  late final TaskRepository _tasks;
  List<Task> _items = <Task>[];
  bool _onlyOpen = true;
  String _search = '';

  @override
  void initState() {
    super.initState();
    _tasks = TaskRepository(widget.database);
    _load();
  }

  Future<void> _load() async {
    final List<Task> items = await _tasks.list(onlyOpen: _onlyOpen, search: _search);
    if (!mounted) return;
    setState(() => _items = items);
  }

  Future<void> _newTask() async {
    final bool? made = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => _TaskDialog(repository: _tasks),
    );
    if (made == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: _newTask,
        tooltip: 'کار تازه',
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    decoration: const InputDecoration(
                      hintText: 'جست‌وجوی کارها',
                      prefixIcon: Icon(Icons.search),
                    ),
                    onChanged: (String value) {
                      _search = value;
                      _load();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: Text(_onlyOpen ? 'باز' : 'همه'),
                  selected: _onlyOpen,
                  onSelected: (bool value) {
                    setState(() => _onlyOpen = value);
                    _load();
                  },
                ),
              ],
            ),
          ),
          Expanded(
            child: SelectionList<Task>(
              items: _items,
              itemKey: (Task task) => ValueKey<int>(task.id),
              selectionHint: 'کار انتخاب‌شده',
              empty: Center(child: Text(Fa.t('nav.tasks'))),
              onDelete: (List<Task> items) async {
                for (final Task task in items) {
                  await _tasks.softDelete(task.id);
                }
                await _load();
              },
              itemBuilder: (
                BuildContext context,
                Task task,
                bool selected,
                VoidCallback onTap,
              ) {
                return CheckboxListTile(
                  value: selected,
                  onChanged: (bool? value) => onTap(),
                  title: Text(
                    task.title,
                    style: TextStyle(
                      decoration: task.isDone ? TextDecoration.lineThrough : null,
                      color: task.isOpen ? null : Theme.of(context).hintColor,
                    ),
                  ),
                  subtitle: Text(
                    <String>[
                      task.context,
                      if (task.effortMinutes != null) '${task.effortMinutes} دقیقه',
                      if (task.dueAt != null) task.dueAt!.substring(0, 10),
                    ].join(' • '),
                  ),
                  secondary: task.isDone
                      ? IconButton(
                          tooltip: 'بازکردن',
                          onPressed: () async {
                            await _tasks.setStatus(task.id, 'todo');
                            await _load();
                          },
                          icon: const Icon(Icons.undo),
                        )
                      : IconButton(
                          tooltip: 'انجام شد',
                          onPressed: () async {
                            await _tasks.setStatus(task.id, 'done');
                            await _load();
                          },
                          icon: const Icon(Icons.check_circle_outline),
                        ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// The dialog that writes a new task.
class _TaskDialog extends StatefulWidget {
  const _TaskDialog({required this.repository});

  final TaskRepository repository;

  @override
  State<_TaskDialog> createState() => _TaskDialogState();
}

class _TaskDialogState extends State<_TaskDialog> {
  final TextEditingController _title = TextEditingController();
  final TextEditingController _notes = TextEditingController();
  String _context = 'personal';

  @override
  void dispose() {
    _title.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('کار تازه'),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            TextField(
              controller: _title,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'عنوان'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _notes,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'توضیح'),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _context,
              decoration: const InputDecoration(labelText: 'گستره'),
              items: const <DropdownMenuItem<String>>[
                DropdownMenuItem<String>(value: 'company', child: Text('کار')),
                DropdownMenuItem<String>(value: 'personal', child: Text('شخصی')),
                DropdownMenuItem<String>(value: 'learning', child: Text('یادگیری')),
              ],
              onChanged: (String? value) {
                if (value != null) setState(() => _context = value);
              },
            ),
          ],
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('نه'),
        ),
        FilledButton(
          onPressed: () async {
            final String title = _title.text.trim();
            if (title.isEmpty) return;
            await widget.repository
                .create(title: title, descriptionMd: _notes.text, context: _context);
            if (context.mounted) Navigator.of(context).pop(true);
          },
          child: const Text('بگذار'),
        ),
      ],
    );
  }
}
