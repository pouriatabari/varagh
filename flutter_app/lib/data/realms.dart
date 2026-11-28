/// The realms of the map and the campaign that gives them.
library;

import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:sqflite/sqflite.dart';

import '../i18n.dart';
import 'tasks.dart';

/// A realm of the map.
class Realm {
  const Realm({
    required this.key,
    required this.nameFa,
    required this.coverageFa,
    required this.legendFa,
    required this.adjacent,
    required this.start,
    required this.hidden,
  });

  final String key;
  final String nameFa;
  final String coverageFa;
  final String legendFa;
  final List<String> adjacent;
  final bool start;
  final bool hidden;

  /// Read a realm out of a row of the vendored file.
  static Realm fromJson(String key, Map<String, Object?> row) {
    return Realm(
      key: key,
      nameFa: row['name_fa'] as String? ?? key,
      coverageFa: row['coverage_fa'] as String? ?? '',
      legendFa: row['legend_fa'] as String? ?? '',
      adjacent: (row['adjacent'] as List<dynamic>? ?? <dynamic>[])
          .map((Object? value) => '$value')
          .toList(),
      start: row['start'] as bool? ?? false,
      hidden: row['hidden'] as bool? ?? false,
    );
  }
}

/// The state of a realm of the map.
class RealmState {
  const RealmState({
    required this.realm,
    required this.state,
    this.castlesLit = 0,
    this.domainName,
    this.assignedAt = '',
  });

  final Realm realm;

  /// One of fog / progress / claimed / hidden.
  final String state;
  final int castlesLit;
  final String? domainName;

  /// When the realm was given to a domain: the order of the campaign.
  final String assignedAt;
}

/// The reading and the writing of the realms.
class RealmRepository {
  const RealmRepository(this.db);

  final Database db;

  /// The vendored realms of the map.
  static Future<Map<String, Realm>> allRealms() async {
    final String text = await rootBundle.loadString('assets/realms.json');
    final Map<String, Object?> parsed = jsonDecode(text) as Map<String, Object?>;
    final List<dynamic> rows = parsed['realms'] as List<dynamic>;
    final Map<String, Realm> realms = <String, Realm>{};
    for (final Object? row in rows) {
      final Map<String, Object?> map = row as Map<String, Object?>;
      final Realm realm = Realm.fromJson(map['key'] as String, map);
      realms[realm.key] = realm;
    }
    return realms;
  }

  /// The claims of the user.
  Future<List<RealmClaim>> listClaims() async {
    final List<Map<String, Object?>> rows = await db.query(
      'realm_claims',
      orderBy: 'assigned_at ASC',
    );
    return rows.map(RealmClaim.fromRow).toList();
  }

  /// The state of every realm.
  Future<List<RealmState>> states() async {
    final Map<String, Realm> realms = await allRealms();
    final List<RealmClaim> claims = await listClaims();
    final Map<String, RealmClaim> byKey = <String, RealmClaim>{
      for (final RealmClaim claim in claims) claim.realmKey: claim,
    };
    final Map<String, int> fiefs = await _fiefsByDomain();
    final List<RealmState> states = <RealmState>[];
    for (final Realm realm in realms.values) {
      final RealmClaim? claim = byKey[realm.key];
      if (claim == null) {
        states.add(RealmState(realm: realm, state: 'fog'));
        continue;
      }
      final int castles = (fiefs[claim.domainName ?? ''] ?? 0).clamp(0, 3);
      states.add(
        RealmState(
          realm: realm,
          state: claim.claimedAt != null ? 'claimed' : 'progress',
          castlesLit: castles,
          domainName: claim.domainName,
          assignedAt: claim.assignedAt,
        ),
      );
    }
    return states;
  }

  /// The number of fiefs a domain has earned, by name.
  Future<Map<String, int>> _fiefsByDomain() async {
    final List<Map<String, Object?>> rows = await db.rawQuery('''
      SELECT d.name AS name, COUNT(m.id) AS total
      FROM domains d
      LEFT JOIN medals m ON m.domain_id = d.id AND m.value_counted > 0
      GROUP BY d.id
    ''');
    final Map<String, int> out = <String, int>{};
    for (final Map<String, Object?> row in rows) {
      final int total = (row['total'] as int?) ?? 0;
      out[(row['name'] as String?) ?? ''] = total ~/ 3;
    }
    return out;
  }

  /// The realms a domain may take, with the rules of the campaign.
  Future<List<Realm>> assignable() async {
    final Map<String, Realm> realms = await allRealms();
    final Set<String> taken = (await listClaims())
        .map((RealmClaim claim) => claim.realmKey)
        .toSet();
    final List<Realm> candidates = <Realm>[];
    for (final Realm realm in realms.values) {
      if (taken.contains(realm.key)) continue;
      if (realm.hidden) continue;
      if (taken.isEmpty) {
        if (realm.start) candidates.add(realm);
        continue;
      }
      if (realm.adjacent.any(taken.contains)) candidates.add(realm);
    }
    return candidates;
  }

  /// Give a realm to a domain: the user has begun the campaign.
  Future<void> assign(String realmKey, String domainName) async {
    final int domainId = await DomainRepository(db).create(domainName);
    await db.insert('realm_claims', <String, Object?>{
      'realm_key': realmKey,
      'domain_id': domainId,
      'domain_name': domainName,
      'assigned_at': DateTime.now().toUtc().toIso8601String(),
      'claimed_at': null,
    });
  }

  /// Finish the campaign: the realm is won.
  Future<void> claim(String realmKey) async {
    await db.update(
      'realm_claims',
      <String, Object?>{'claimed_at': DateTime.now().toUtc().toIso8601String()},
      where: 'realm_key = ?',
      whereArgs: <Object?>[realmKey],
    );
  }

  /// Make sure the start realm of the map has a seed.
  Future<void> seedStart() async {
    final List<Map<String, Object?>> rows = await db.query(
      'realm_claims',
      columns: <String>['id'],
      limit: 1,
    );
    if (rows.isNotEmpty) return;
    final Map<String, Realm> realms = await allRealms();
    for (final Realm realm in realms.values) {
      if (realm.start) {
        await assign(realm.key, 'first');
        return;
      }
    }
  }
}

/// A row of the realm_claims table.
class RealmClaim {
  const RealmClaim({
    required this.realmKey,
    required this.domainId,
    required this.domainName,
    required this.assignedAt,
    required this.claimedAt,
  });

  final String realmKey;
  final int? domainId;
  final String? domainName;
  final String assignedAt;
  final String? claimedAt;

  static RealmClaim fromRow(Map<String, Object?> row) {
    return RealmClaim(
      realmKey: row['realm_key']! as String,
      domainId: row['domain_id'] as int?,
      domainName: row['domain_name'] as String?,
      assignedAt: row['assigned_at'] as String? ?? '',
      claimedAt: row['claimed_at'] as String?,
    );
  }
}

/// The words of the realm states.
String realmStateWord(String state) {
  switch (state) {
    case 'claimed':
      return 'تسخیرشده';
    case 'progress':
      return 'در راه';
    case 'hidden':
      return 'نهفته';
    default:
      return 'در مه';
  }
}

/// The word of the legend of a realm.
String realmLegend(RealmState state) => state.realm.legendFa.isEmpty
    ? Fa.t('nav.realms')
    : state.realm.legendFa;

/// The word of the coverage of a realm.
String realmCoverage(RealmState state) => state.realm.coverageFa;
