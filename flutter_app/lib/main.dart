/// The entry of the app.
library;

import 'package:flutter/material.dart';

import 'app.dart';
import 'data/database.dart';
import 'domain/rewards_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final database = await openJournal();
  final config = await RewardsConfig.load();
  final themeName = await readSetting(database, 'theme') ?? 'night';
  runApp(VaraghApp(database: database, config: config, themeName: themeName));
}
