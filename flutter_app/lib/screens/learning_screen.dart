/// The learning: the items of the syllabus and how far they came.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../i18n.dart';

/// The learning items of the user.
class LearningScreen extends StatefulWidget {
  const LearningScreen({super.key, required this.database});

  final Database database;

  @override
  State<LearningScreen> createState() => _LearningScreenState();
}

class _LearningScreenState extends State<LearningScreen> {
  List<Map<String, Object?>> _items = <Map<String, Object?>>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<Map<String, Object?>> rows = await widget.database.query(
      'learning_items',
      where: 'deleted_at IS NULL',
      orderBy: 'created_at DESC',
      limit: 200,
    );
    if (!mounted) return;
    setState(() => _items = rows);
  }

  @override
  Widget build(BuildContext context) {
    if (_items.isEmpty) {
      return Center(child: Text(Fa.t('nav.learning')));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: _items.length,
      separatorBuilder: (BuildContext context, int index) => const Divider(height: 1),
      itemBuilder: (BuildContext context, int index) {
        final Map<String, Object?> item = _items[index];
        return ListTile(
          title: Text('${item['title'] ?? ''}'),
          subtitle: Text('${item['unit'] ?? ''}'),
        );
      },
    );
  }
}
