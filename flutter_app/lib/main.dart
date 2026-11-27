/// The entry of the app.
library;

import 'package:flutter/material.dart';

import 'app.dart';
import 'data/database.dart';
import 'domain/rewards_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final Database database = await openJournal();
  final RewardsConfig config = await RewardsConfig.load();
  final String themeName = await readSetting(database, 'theme') ?? 'night';
  runApp(VaraghApp(database: database, config: config, themeName: themeName));
}
