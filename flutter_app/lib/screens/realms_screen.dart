/// The map of the realms: the ground, the fog and the campaign road.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/realms.dart';
import '../i18n.dart';
import '../theme.dart';
import '../widgets/realm_map.dart';

/// The map: the picture of the realms and the panel of the one that is
/// picked.
class RealmsScreen extends StatefulWidget {
  const RealmsScreen({super.key, required this.database});

  final Database database;

  @override
  State<RealmsScreen> createState() => _RealmsScreenState();
}

class _RealmsScreenState extends State<RealmsScreen> {
  late final RealmRepository _realms;
  MapGeometry? _geometry;
  List<RealmState> _states = <RealmState>[];
  RealmState? _selected;

  @override
  void initState() {
    super.initState();
    _realms = RealmRepository(widget.database);
    _load();
  }

  Future<void> _load() async {
    await _realms.seedStart();
    final MapGeometry geometry = await MapGeometry.load();
    final List<RealmState> states = await _realms.states();
    if (!mounted) return;
    setState(() {
      _geometry = geometry;
      _states = states;
      _selected ??= states.isEmpty ? null : states.first;
    });
  }

  @override
  Widget build(BuildContext context) {
    final MapGeometry? geometry = _geometry;
    if (geometry == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final AppPalette palette = Theme.of(context).brightness == Brightness.dark
        ? AppPalette.night
        : AppPalette.parchment;

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 900;
        final Widget picture = Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: palette.border),
          ),
          clipBehavior: Clip.antiAlias,
          child: SizedBox(
            height: wide ? 620 : 460,
            child: RealmMapView(
              geometry: geometry,
              states: _states,
              palette: palette,
              selectedKey: _selected?.realm.key,
              onRealmTap: (RealmState state) => setState(() => _selected = state),
            ),
          ),
        );

        final Widget panel = _RealmPanel(
          state: _selected,
          onClaim: _selected == null
              ? null
              : () async {
                  await _realms.claim(_selected!.realm.key);
                  await _load();
                },
        );

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

/// The panel of the realm that is picked.
class _RealmPanel extends StatelessWidget {
  const _RealmPanel({required this.state, this.onClaim});

  final RealmState? state;
  final VoidCallback? onClaim;

  @override
  Widget build(BuildContext context) {
    final RealmState? picked = state;
    if (picked == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Text(Fa.t('nav.realms')),
        ),
      );
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(picked.realm.nameFa, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              picked.realm.coverageFa,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Chip(label: Text(realmStateWord(picked.state))),
            const SizedBox(height: 8),
            Text(realmLegend(picked)),
            if (picked.domainName != null) ...<Widget>[
              const SizedBox(height: 8),
              Text('قلمرو: ${picked.domainName}'),
            ],
            if (onClaim != null) ...<Widget>[
              const SizedBox(height: 12),
              FilledButton(onPressed: onClaim, child: const Text('تسخیر')),
            ],
          ],
        ),
      ),
    );
  }
}
