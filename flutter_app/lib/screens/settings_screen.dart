/// The settings of the user: the theme of the app and the place of the
/// journal.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/database.dart';

/// The settings of the app.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({
    super.key,
    required this.database,
    required this.themeName,
    required this.onThemeChanged,
  });

  final Database database;
  final String themeName;
  final ValueChanged<String> onThemeChanged;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        Text('پوسته', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        SegmentedButton<String>(
          segments: const <ButtonSegment<String>>[
            ButtonSegment<String>(value: 'night', label: Text('شب')),
            ButtonSegment<String>(value: 'parchment', label: Text('کاغذ')),
          ],
          selected: <String>{widget.themeName},
          onSelectionChanged: (Set<String> selection) async {
            final String name = selection.first;
            await writeSetting(widget.database, 'theme', name);
            widget.onThemeChanged(name);
          },
        ),
        const Divider(height: 32),
        Text('دفتر', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        const Text(
          'دفترِ تو روی همین دستگاه می‌ماند و به هیچ‌جا فرستاده نمی‌شود. '
          'نام فایل: varagh.db',
        ),
      ],
    );
  }
}
