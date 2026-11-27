/// The SQLite of the desktop: the library that needs no plugin.
library;

import 'dart:io';

import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// Prepare the factory of the journal on the desktop.
///
/// The phone has the SQLite of the system, so the factory of the plugin is
/// left alone there.
void prepareDatabaseFactory() {
  if (Platform.isAndroid || Platform.isIOS) return;
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
}
