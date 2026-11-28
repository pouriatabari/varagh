/// The dashboard: the counters of the journal and the tree of the ranks.
library;

import 'package:flutter/material.dart';

import '../data/database.dart';
import '../data/time_entries.dart';
import '../domain/rewards_config.dart';
import '../domain/skill_tree.dart';
import '../i18n.dart';
import '../theme.dart';
import '../widgets/skill_tree.dart';
import '../widgets/timer_card.dart';

/// The first page: what the day holds and where the user stands.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.database, required this.config});

  final Database database;
  final RewardsConfig config;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  SkillTree? _tree;
  int _open = 0;
  int _minutes = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final HonoursSnapshot snapshot = await HonoursSnapshot.read(widget.database);
    final List<Map<String, Object?>> rows = await widget.database.query(
      'tasks',
      columns: <String>['id', 'status'],
    );
    int open = 0;
    for (final Map<String, Object?> row in rows) {
      final String status = row['status'] as String? ?? 'todo';
      if (status == 'todo' || status == 'doing') open++;
    }
    final int minutes =
        await TimeRepository(widget.database).minutesToday();
    final SkillTree tree = buildSkillTree(
      medals: snapshot.medals,
      musters: snapshot.musters,
      reachedTitles: snapshot.reachedTitles,
      config: widget.config,
      titleName: Fa.title,
      gateName: Fa.gate,
    );
    if (!mounted) return;
    setState(() {
      _tree = tree;
      _open = open;
      _minutes = minutes;
    });
  }

  @override
  Widget build(BuildContext context) {
    final SkillTree? tree = _tree;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        TimerCard(database: widget.database),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: <Widget>[
            _Tile(label: 'کارهای باز', value: '$_open'),
            _Tile(label: 'دقایق امروز', value: '$_minutes'),
            if (tree != null)
              _Tile(label: 'رتبهٔ کنونی', value: Fa.title(tree.current)),
          ],
        ),
        const SizedBox(height: 16),
        if (tree != null) ...<Widget>[
          Text(
            Fa.t('honours.tree_title'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: (Theme.of(context).brightness == Brightness.dark
                        ? AppPalette.night
                        : AppPalette.parchment)
                    .gilt
                    .withValues(alpha: 0.38),
              ),
            ),
            clipBehavior: Clip.antiAlias,
            child: SizedBox(
              height: 320,
              child: SkillTreeView(
                tree: tree,
                palette: Theme.of(context).brightness == Brightness.dark
                    ? AppPalette.night
                    : AppPalette.parchment,
                onNodeTap: (TreeNode node) {},
              ),
            ),
          ),
        ],
      ],
    );
  }
}

/// One number of the dashboard.
class _Tile extends StatelessWidget {
  const _Tile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 180,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(value, style: Theme.of(context).textTheme.headlineMedium),
          Text(label, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
