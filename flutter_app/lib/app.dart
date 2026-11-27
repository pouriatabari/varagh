/// The shell of the app: the navigation, the theme and the language.
library;

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import 'data/database.dart';
import 'domain/rewards_config.dart';
import 'domain/skill_tree.dart';
import 'i18n.dart';
import 'screens/dashboard_screen.dart';
import 'screens/honours_screen.dart';
import 'screens/learning_screen.dart';
import 'screens/reviews_screen.dart';
import 'screens/tasks_screen.dart';
import 'theme.dart';

/// The app of the user: the journal, in Persian, on every screen.
class VaraghApp extends StatelessWidget {
  const VaraghApp({
    super.key,
    required this.database,
    required this.config,
    required this.themeName,
  });

  final Database database;
  final RewardsConfig config;
  final String themeName;

  @override
  Widget build(BuildContext context) {
    final AppPalette palette =
        themeName == 'parchment' ? AppPalette.parchment : AppPalette.night;
    return MaterialApp(
      title: Fa.t('app.name'),
      debugShowCheckedModeBanner: false,
      theme: buildTheme(palette),
      locale: const Locale('fa'),
      supportedLocales: const <Locale>[Locale('fa'), Locale('en')],
      builder: (BuildContext context, Widget? child) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: HomeShell(database: database, config: config, palette: palette),
    );
  }
}

/// The pages of the app.
class _Page {
  const _Page(this.key, this.icon, this.builder);

  final String key;
  final IconData icon;
  final WidgetBuilder builder;
}

/// The shell: a rail on the wide screens, a bar on the narrow ones.
class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.database,
    required this.config,
    required this.palette,
  });

  final Database database;
  final RewardsConfig config;
  final AppPalette palette;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final List<_Page> pages = <_Page>[
      _Page(
        'dashboard',
        Icons.dashboard_outlined,
        (BuildContext context) =>
            DashboardScreen(database: widget.database, config: widget.config),
      ),
      _Page(
        'tasks',
        Icons.checklist_outlined,
        (BuildContext context) => TasksScreen(database: widget.database),
      ),
      _Page(
        'learning',
        Icons.menu_book_outlined,
        (BuildContext context) => LearningScreen(database: widget.database),
      ),
      _Page(
        'reviews',
        Icons.assessment_outlined,
        (BuildContext context) => ReviewsScreen(database: widget.database),
      ),
      _Page(
        'honours',
        Icons.military_tech_outlined,
        (BuildContext context) => HonoursScreen(
          database: widget.database,
          config: widget.config,
        ),
      ),
    ];

    final Widget body = Scaffold(
      appBar: AppBar(
        title: Text(Fa.t('app.name')),
        actions: <Widget>[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Center(child: Text(Fa.t('nav.${pages[_index].key}'))),
          ),
        ],
      ),
      body: SafeArea(child: pages[_index].builder(context)),
    );

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        if (constraints.maxWidth >= 900) {
          return Scaffold(
            body: Row(
              children: <Widget>[
                NavigationRail(
                  selectedIndex: _index,
                  onDestinationSelected: (int index) => setState(() => _index = index),
                  labelType: NavigationRailLabelType.all,
                  destinations: pages
                      .map(
                        (_Page page) => NavigationRailDestination(
                          icon: Icon(page.icon),
                          label: Text(Fa.t('nav.${page.key}')),
                        ),
                      )
                      .toList(),
                ),
                const VerticalDivider(width: 1),
                Expanded(child: body),
              ],
            ),
          );
        }
        return Scaffold(
          body: body,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _index,
            onDestinationSelected: (int index) => setState(() => _index = index),
            destinations: pages
                .map(
                  (_Page page) => NavigationDestination(
                    icon: Icon(page.icon),
                    label: Fa.t('nav.${page.key}'),
                  ),
                )
                .toList(),
          ),
        );
      },
    );
  }
}

/// The tree of the ranks, built out of the journal of the user.
Future<SkillTree> buildTreeOfUser(
  Database database,
  RewardsConfig config,
) async {
  final HonoursSnapshot snapshot = await HonoursSnapshot.read(database);
  return buildSkillTree(
    medals: snapshot.medals,
    musters: snapshot.musters,
    reachedTitles: snapshot.reachedTitles,
    config: config,
    titleName: Fa.title,
    gateName: Fa.gate,
  );
}
