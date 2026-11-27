/// The learning: the items of the syllabus and how far they came.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/learning.dart';
import '../i18n.dart';
import '../widgets/selection_list.dart';

/// The learning items of the user.
class LearningScreen extends StatefulWidget {
  const LearningScreen({super.key, required this.database});

  final Database database;

  @override
  State<LearningScreen> createState() => _LearningScreenState();
}

class _LearningScreenState extends State<LearningScreen> {
  late final LearningRepository _items;
  List<LearningItem> _list = <LearningItem>[];
  bool _onlyActive = true;

  @override
  void initState() {
    super.initState();
    _items = LearningRepository(widget.database);
    _load();
  }

  Future<void> _load() async {
    final List<LearningItem> list = await _items.list(onlyActive: _onlyActive);
    if (!mounted) return;
    setState(() => _list = list);
  }

  Future<void> _newItem() async {
    final bool? made = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => _LearningDialog(repository: _items),
    );
    if (made == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: _newItem,
        tooltip: 'درس تازه',
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Align(
              alignment: Alignment.centerRight,
              child: FilterChip(
                label: Text(_onlyActive ? 'در جریان' : 'همه'),
                selected: _onlyActive,
                onSelected: (bool value) {
                  setState(() => _onlyActive = value);
                  _load();
                },
              ),
            ),
          ),
          Expanded(
            child: SelectionList<LearningItem>(
              items: _list,
              itemKey: (LearningItem item) => ValueKey<int>(item.id),
              selectionHint: 'درس انتخاب‌شده',
              empty: Center(child: Text(Fa.t('nav.learning'))),
              onDelete: (List<LearningItem> items) async {
                for (final LearningItem item in items) {
                  await _items.softDelete(item.id);
                }
                await _load();
              },
              itemBuilder: (
                BuildContext context,
                LearningItem item,
                bool selected,
                VoidCallback onTap,
              ) {
                return CheckboxListTile(
                  value: selected,
                  onChanged: (bool? value) => onTap(),
                  title: Text(item.title),
                  subtitle: Text(
                    <String>[
                      item.unit,
                      item.progress,
                    ].where((String part) => part.isNotEmpty).join(' • '),
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

/// The dialog that writes a new item of the learning.
class _LearningDialog extends StatefulWidget {
  const _LearningDialog({required this.repository});

  final LearningRepository repository;

  @override
  State<_LearningDialog> createState() => _LearningDialogState();
}

class _LearningDialogState extends State<_LearningDialog> {
  final TextEditingController _title = TextEditingController();
  final TextEditingController _unit = TextEditingController();
  final TextEditingController _progress = TextEditingController();

  @override
  void dispose() {
    _title.dispose();
    _unit.dispose();
    _progress.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('درس تازه'),
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
              controller: _unit,
              decoration: const InputDecoration(labelText: 'واحد'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _progress,
              decoration: const InputDecoration(labelText: 'پیشرفت'),
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
            await widget.repository.create(
              title: title,
              unit: _unit.text.trim(),
              progress: _progress.text.trim(),
            );
            if (context.mounted) Navigator.of(context).pop(true);
          },
          child: const Text('بگذار'),
        ),
      ],
    );
  }
}
