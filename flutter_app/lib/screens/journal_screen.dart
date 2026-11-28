/// The journal of the user: a note for the day.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/journal.dart';
import '../i18n.dart';
import '../utils/jalali.dart';
import '../widgets/selection_list.dart';

/// The journal: the notes of the user.
class JournalScreen extends StatefulWidget {
  const JournalScreen({super.key, required this.database});

  final Database database;

  @override
  State<JournalScreen> createState() => _JournalScreenState();
}

class _JournalScreenState extends State<JournalScreen> {
  JournalRepository get _journal => JournalRepository(widget.database);
  List<JournalEntry> _entries = <JournalEntry>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<JournalEntry> entries = await _journal.list();
    if (!mounted) return;
    setState(() => _entries = entries);
  }

  Future<void> _newEntry() async {
    final JalaliDate today = jalaliOf(DateTime.now());
    final made = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => _JournalDialog(
        repository: _journal,
        dateKey: today.plain,
      ),
    );
    if (made == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: _newEntry,
        tooltip: 'یادداشت تازه',
        child: const Icon(Icons.add),
      ),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              jalaliOf(DateTime.now()).persian,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          Expanded(
            child: SelectionList<JournalEntry>(
              items: _entries,
              itemKey: (JournalEntry entry) => ValueKey<int>(entry.id),
              selectionHint: 'یادداشت انتخاب‌شده',
              empty: Center(child: Text(Fa.t('nav.journal'))),
              onDelete: (List<JournalEntry> items) async {
                for (final JournalEntry entry in items) {
                  await _journal.delete(entry.id);
                }
                await _load();
              },
              itemBuilder: (
                BuildContext context,
                JournalEntry entry,
                bool selected,
                VoidCallback onTap,
              ) {
                return ListTile(
                  leading: Checkbox(
                    value: selected,
                    onChanged: (bool? value) => onTap(),
                  ),
                  title: Text(entry.dateKey),
                  subtitle: Text(
                    entry.text,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
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

/// The dialog that writes a new note of the journal.
class _JournalDialog extends StatefulWidget {
  const _JournalDialog({required this.repository, required this.dateKey});

  final JournalRepository repository;
  final String dateKey;

  @override
  State<_JournalDialog> createState() => _JournalDialogState();
}

class _JournalDialogState extends State<_JournalDialog> {
  final TextEditingController _text = TextEditingController();

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.dateKey),
      content: SizedBox(
        width: 380,
        child: TextField(
          controller: _text,
          autofocus: true,
          maxLines: 6,
          decoration: const InputDecoration(labelText: 'یادداشت'),
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('نه'),
        ),
        FilledButton(
          onPressed: () async {
            final String text = _text.text.trim();
            if (text.isEmpty) return;
            await widget.repository.create(
              dateKey: widget.dateKey,
              text: text,
            );
            if (context.mounted) Navigator.of(context).pop(true);
          },
          child: const Text('بگذار'),
        ),
      ],
    );
  }
}
