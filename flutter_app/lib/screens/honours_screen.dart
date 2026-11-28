/// The hall of honours: the court chart and the panel of the tier that is
/// picked.
library;

import 'package:flutter/material.dart';
import '../data/database.dart';
import '../domain/rewards_config.dart';
import '../domain/skill_tree.dart';
import '../i18n.dart';
import '../theme.dart';
import '../widgets/court_chart.dart';

/// The hall: the court chart and the panel of the tier that is picked.
class HonoursScreen extends StatefulWidget {
  const HonoursScreen({super.key, required this.database, required this.config});

  final Database database;
  final RewardsConfig config;

  @override
  State<HonoursScreen> createState() => _HonoursScreenState();
}

class _HonoursScreenState extends State<HonoursScreen> {
  SkillTree? _tree;
  TreeNode? _selected;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final HonoursSnapshot snapshot = await HonoursSnapshot.read(widget.database);
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
      _selected = tree.nodeOf('rank:${tree.current}');
    });
  }

  @override
  Widget build(BuildContext context) {
    final SkillTree? tree = _tree;
    if (tree == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final AppPalette palette = Theme.of(context).brightness == Brightness.dark
        ? AppPalette.night
        : AppPalette.parchment;

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 900;
        final Widget picture = Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              Fa.t('honours.court'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            Text(
              Fa.t('honours.tap_to_choose'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: palette.gilt.withValues(alpha: 0.38)),
              ),
              clipBehavior: Clip.antiAlias,
              child: SizedBox(
                height: 420,
                child: CourtChartView(
                  tree: tree,
                  config: widget.config,
                  palette: palette,
                  selectedKey: _selected?.id,
                  onTap: (TreeNode node) => setState(() => _selected = node),
                ),
              ),
            ),
          ],
        );

        final Widget panel = _NodePanel(node: _selected, config: widget.config);

        if (wide) {
          return Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(flex: 3, child: picture),
                const SizedBox(width: 16),
                Expanded(flex: 1, child: panel),
              ],
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.all(16),
          children: <Widget>[picture, const SizedBox(height: 16), panel],
        );
      },
    );
  }
}

/// The detail of the tier that is picked.
class _NodePanel extends StatelessWidget {
  const _NodePanel({required this.node, required this.config});

  final TreeNode? node;
  final RewardsConfig config;

  @override
  Widget build(BuildContext context) {
    final TreeNode? picked = node;
    if (picked == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(Fa.t('honours.tap_to_choose')),
        ),
      );
    }

    final TitleRule? rule = _ruleOf(config, picked.titleKey);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(picked.label, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Chip(label: Text(_stateWord(picked.state))),
            const SizedBox(height: 12),
            if (rule != null) ...<Widget>[
              Text(
                Fa.t('honours.requirements'),
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 4),
              Text('${rule.degrees} ${Fa.t('gate.degrees')}'),
            ],
          ],
        ),
      ),
    );
  }

  String _stateWord(String state) {
    switch (state) {
      case NodeState.current:
        return Fa.t('honours.current');
      case NodeState.next:
        return Fa.t('honours.next');
      case NodeState.reached:
        return Fa.t('honours.reached');
      default:
        return Fa.t('honours.locked');
    }
  }
}

/// The rule of a title of the ladder.
TitleRule? _ruleOf(RewardsConfig config, String key) {
  for (final TitleRule rule in config.titles) {
    if (rule.key == key) return rule;
  }
  return null;
}
