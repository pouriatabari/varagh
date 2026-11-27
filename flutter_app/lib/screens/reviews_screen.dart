/// The reviews: the periods of the user and their state.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../i18n.dart';

/// The reviews of the user.
class ReviewsScreen extends StatefulWidget {
  const ReviewsScreen({super.key, required this.database});

  final Database database;

  @override
  State<ReviewsScreen> createState() => _ReviewsScreenState();
}

class _ReviewsScreenState extends State<ReviewsScreen> {
  List<Map<String, Object?>> _reviews = <Map<String, Object?>>[];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<Map<String, Object?>> rows = await widget.database.query(
      'reviews',
      orderBy: 'period_start DESC',
      limit: 200,
    );
    if (!mounted) return;
    setState(() => _reviews = rows);
  }

  @override
  Widget build(BuildContext context) {
    if (_reviews.isEmpty) {
      return Center(child: Text(Fa.t('nav.reviews')));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: _reviews.length,
      separatorBuilder: (BuildContext context, int index) => const Divider(height: 1),
      itemBuilder: (BuildContext context, int index) {
        final Map<String, Object?> review = _reviews[index];
        return ListTile(
          title: Text('${review['period_type'] ?? ''}'),
          subtitle: Text('${review['period_start'] ?? ''} — ${review['period_end'] ?? ''}'),
          trailing: Text('${review['status'] ?? ''}'),
        );
      },
    );
  }
}
