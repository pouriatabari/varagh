/// The reviews: the periods of the user and the muster that gives the
/// medals.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/muster.dart';
import '../domain/rewards_config.dart';
import '../i18n.dart';
import '../utils/jalali.dart';

/// The reviews of the user.
class ReviewsScreen extends StatefulWidget {
  const ReviewsScreen({
    super.key,
    required this.database,
    required this.config,
    required this.onChanged,
  });

  final Database database;
  final RewardsConfig config;

  /// The call when the medals were given, so the hall can be read again.
  final VoidCallback onChanged;

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

  Future<void> _newMuster() async {
    final DateTime now = DateTime.now();
    final JalaliDate month = jalaliOf(now);
    await widget.database.insert('reviews', <String, Object?>{
      'period_type': 'month',
      'period_start': month.plain,
      'period_end': month.plain,
      'status': 'draft',
      'stats': '{}',
      'created_at': DateTime.now().toUtc().toIso8601String(),
    });
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: _newMuster,
        tooltip: 'مستر تازه',
        child: const Icon(Icons.add),
      ),
      body: _reviews.isEmpty
          ? Center(child: Text(Fa.t('nav.reviews')))
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: _reviews.length,
              separatorBuilder: (BuildContext context, int index) =>
                  const Divider(height: 1),
              itemBuilder: (BuildContext context, int index) {
                final Map<String, Object?> review = _reviews[index];
                return ListTile(
                  title: Text('${review['period_start'] ?? ''}'),
                  subtitle: Text('${review['status'] ?? ''}'),
                  trailing: const Icon(Icons.chevron_left),
                  onTap: () => _openReview(review),
                );
              },
            ),
    );
  }

  Future<void> _openReview(Map<String, Object?> review) async {
    final int id = review['id']! as int;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => MusterScreen(
          database: widget.database,
          config: widget.config,
          reviewId: id,
          onChanged: () {
            widget.onChanged();
            _load();
          },
        ),
      ),
    );
    await _load();
  }
}

/// The muster of one period: the proposals, the finished tasks and the
/// ceremony.
class MusterScreen extends StatefulWidget {
  const MusterScreen({
    super.key,
    required this.database,
    required this.config,
    required this.reviewId,
    required this.onChanged,
  });

  final Database database;
  final RewardsConfig config;
  final int reviewId;
  final VoidCallback onChanged;

  @override
  State<MusterScreen> createState() => _MusterScreenState();
}

class _MusterScreenState extends State<MusterScreen> {
  final Set<int> _picked = <int>{};
  List<Map<String, Object?>> _finished = <Map<String, Object?>>[];
  List<Map<String, Object?>> _proposals = <Map<String, Object?>>[];
  List<String> _skipped = <String>[];
  String _tier = 'bronze';
  String _virtue = 'prowess';
  bool _impactNote = false;
  bool _concrete = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final List<Map<String, Object?>> tasks = await widget.database.query(
      'tasks',
      columns: <String>['id', 'title', 'completed_at'],
      where: "status = 'done' AND deleted_at IS NULL",
      orderBy: 'completed_at DESC',
      limit: 200,
    );
    final List<Map<String, Object?>> proposals = await widget.database.query(
      'medal_proposals',
      where: 'review_id = ?',
      whereArgs: <Object?>[widget.reviewId],
      orderBy: 'id ASC',
    );
    if (!mounted) return;
    setState(() {
      _finished = tasks;
      _proposals = proposals;
    });
  }

  Future<void> _addProposal() async {
    if (_picked.isEmpty) return;
    await widget.database.insert('medal_proposals', <String, Object?>{
      'review_id': widget.reviewId,
      'title': _picked.length == 1
          ? '${_finished.length} کار'
          : '${_picked.length} کار',
      'tier': _tier,
      'virtue': _virtue,
      'evidence_task_ids': _picked.join(','),
      'impact_note': _impactNote ? 1 : 0,
      'concrete': _concrete ? 1 : 0,
    });
    setState(_picked.clear);
    await _load();
  }

  Future<void> _removeProposal(int id) async {
    await widget.database.delete(
      'medal_proposals',
      where: 'id = ?',
      whereArgs: <Object?>[id],
    );
    await _load();
  }

  Future<void> _give() async {
    final List<MedalProposal> proposals = <MedalProposal>[];
    for (final Map<String, Object?> row in _proposals) {
      final List<int> ids = '${row['evidence_task_ids'] ?? ''}'
          .split(',')
          .where((String part) => part.isNotEmpty)
          .map((String part) => int.parse(part))
          .toList();
      proposals.add(
        MedalProposal(
          title: row['title'] as String? ?? '',
          tier: row['tier'] as String? ?? 'bronze',
          virtue: row['virtue'] as String? ?? 'prowess',
          evidenceTaskIds: ids,
          impactNote: (row['impact_note'] as int? ?? 0) == 1,
          concrete: (row['concrete'] as int? ?? 0) == 1,
        ),
      );
    }
    final AwardResult result = await MusterService(widget.database).award(
      reviewId: widget.reviewId,
      proposals: proposals,
      config: widget.config,
    );
    await widget.database.update(
      'reviews',
      <String, Object?>{'status': 'finished'},
      where: 'id = ?',
      whereArgs: <Object?>[widget.reviewId],
    );
    await widget.database.delete(
      'medal_proposals',
      where: 'review_id = ?',
      whereArgs: <Object?>[widget.reviewId],
    );
    if (!mounted) return;
    setState(() => _skipped = result.skipped);
    widget.onChanged();
    await _load();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${result.created.length} مدال داده شد')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('مستر')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          Text('کارهای انجام‌شده', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final Map<String, Object?> task in _finished)
            CheckboxListTile(
              value: _picked.contains(task['id']),
              onChanged: (bool? value) {
                final int id = task['id']! as int;
                setState(() {
                  if (value == true) {
                    _picked.add(id);
                  } else {
                    _picked.remove(id);
                  }
                });
              },
              title: Text('${task['title'] ?? ''}'),
              dense: true,
            ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: <Widget>[
              DropdownButton<String>(
                value: _tier,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(value: 'bronze', child: Text('برنز')),
                  DropdownMenuItem<String>(value: 'silver', child: Text('نقره')),
                  DropdownMenuItem<String>(value: 'gold', child: Text('زر')),
                ],
                onChanged: (String? value) {
                  if (value != null) setState(() => _tier = value);
                },
              ),
              DropdownButton<String>(
                value: _virtue,
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(value: 'prowess', child: Text('توان')),
                  DropdownMenuItem<String>(value: 'valor', child: Text('دلیری')),
                  DropdownMenuItem<String>(value: 'wisdom', child: Text('خرد')),
                  DropdownMenuItem<String>(value: 'loyalty', child: Text('وفاداری')),
                  DropdownMenuItem<String>(value: 'largesse', child: Text('بخشندگی')),
                  DropdownMenuItem<String>(value: 'temperance', child: Text('خویشتن‌داری')),
                ],
                onChanged: (String? value) {
                  if (value != null) setState(() => _virtue = value);
                },
              ),
              FilterChip(
                label: const Text('یادداشت اثر'),
                selected: _impactNote,
                onSelected: (bool value) => setState(() => _impactNote = value),
              ),
              FilterChip(
                label: const Text('ملموس'),
                selected: _concrete,
                onSelected: (bool value) => setState(() => _concrete = value),
              ),
            ],
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: _picked.isEmpty ? null : _addProposal,
            icon: const Icon(Icons.add),
            label: Text('پیشنهاد مدال (${_picked.length} کار)'),
          ),
          const Divider(height: 32),
          Text('پیشنهادها', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final Map<String, Object?> proposal in _proposals)
            ListTile(
              title: Text('${proposal['title'] ?? ''}'),
              subtitle: Text(
                '${proposal['tier'] ?? ''} • ${proposal['virtue'] ?? ''}',
              ),
              trailing: IconButton(
                tooltip: 'برداشتن',
                onPressed: () => _removeProposal(proposal['id']! as int),
                icon: const Icon(Icons.close),
              ),
            ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _proposals.isEmpty ? null : _give,
            child: const Text('دادن مدال‌ها'),
          ),
          for (final String note in _skipped)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(note, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
        ],
      ),
    );
  }
}
