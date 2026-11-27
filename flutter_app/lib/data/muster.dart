/// The muster: the ceremony that gives the medals of a period.
library;

import 'package:sqflite/sqflite.dart';

import '../domain/rewards.dart';
import '../domain/rewards_config.dart';
import '../utils/jalali.dart';

/// A medal that the user proposes for the muster.
class MedalProposal {
  const MedalProposal({
    required this.title,
    required this.tier,
    required this.virtue,
    required this.evidenceTaskIds,
    this.impactNote = false,
    this.concrete = false,
    this.domainName,
  });

  final String title;
  final String tier;
  final String virtue;
  final List<int> evidenceTaskIds;
  final bool impactNote;
  final bool concrete;
  final String? domainName;
}

/// The result of a muster: the medals that were given, and the proposals
/// that were refused with their reason.
class AwardResult {
  const AwardResult({required this.created, required this.skipped});

  final List<int> created;
  final List<String> skipped;
}

/// The service of the muster.
class MusterService {
  const MusterService(this.db);

  final Database db;

  /// Give the medals of a muster.
  ///
  /// The evidence is checked first: the tasks must exist, be finished, be
  /// allowed to count and not back another medal. The tier is clamped to
  /// what the evidence proves, and the value of the month is counted again
  /// after the medals are given.
  Future<AwardResult> award({
    int? reviewId,
    required List<MedalProposal> proposals,
    required RewardsConfig config,
    DateTime? now,
  }) async {
    final DateTime stamp = now ?? DateTime.now().toUtc();
    final String key = monthKeyOf(stamp.toLocal());

    final Set<int> used = await _usedEvidenceIds();
    final List<int> created = <int>[];
    final List<String> skipped = <String>[];

    for (final MedalProposal proposal in proposals) {
      final Object? evidence = await _checkEvidence(proposal, used);
      if (evidence is String) {
        skipped.add('${proposal.title}: $evidence');
        continue;
      }
      final List<int> taskIds = evidence as List<int>;
      final int? domainId = await _domainIdOf(proposal.domainName);
      final String tier = clampedTier(
        proposal.tier,
        taskCount: taskIds.length,
        hasImpactNote: proposal.impactNote,
        concrete: proposal.concrete,
        config: config,
      );
      final int medalId = await db.insert('medals', <String, Object?>{
        'muster_id': reviewId,
        'tier': tier,
        'virtue': proposal.virtue,
        'kind': 'earned',
        'domain_id': domainId,
        'month_key': key,
        'value_raw': config.valueOf(tier),
        'value_counted': 0,
        'awarded_at': stamp.toIso8601String(),
      });
      for (final int taskId in taskIds) {
        await db.insert('medal_evidence', <String, Object?>{
          'medal_id': medalId,
          'task_id': taskId,
        });
        used.add(taskId);
      }
      created.add(medalId);
    }

    await recountMonth(key, config);
    return AwardResult(created: created, skipped: skipped);
  }

  /// The tasks that already back a medal.
  Future<Set<int>> _usedEvidenceIds() async {
    final List<Map<String, Object?>> rows = await db.query('medal_evidence');
    return rows
        .map((Map<String, Object?> row) => row['task_id']! as int)
        .toSet();
  }

  /// The evidence of a proposal: the ids of the tasks, or the reason it
  /// fails.
  Future<Object?> _checkEvidence(MedalProposal proposal, Set<int> used) async {
    if (proposal.evidenceTaskIds.isEmpty) return 'no evidence';
    final List<Map<String, Object?>> rows = await db.query(
      'tasks',
      columns: <String>['id', 'status', 'counts_for_medals'],
      where: 'id IN (${List<String>.filled(proposal.evidenceTaskIds.length, '?').join(',')})',
      whereArgs: proposal.evidenceTaskIds,
    );
    final Set<int> found = rows.map((Map<String, Object?> row) => row['id']! as int).toSet();
    final List<int> missing = proposal.evidenceTaskIds
        .where((int id) => !found.contains(id))
        .toList();
    if (missing.isNotEmpty) return 'unknown tasks: $missing';
    for (final Map<String, Object?> row in rows) {
      final int id = row['id']! as int;
      if (row['status'] != 'done') return 'the task $id is not finished';
      if ((row['counts_for_medals'] as int? ?? 1) != 1) {
        return 'the task $id does not count for the medals';
      }
      if (used.contains(id)) return 'the task $id already backs a medal';
    }
    return List<int>.of(proposal.evidenceTaskIds);
  }

  /// The domain of a name.
  Future<int?> _domainIdOf(String? name) async {
    if (name == null || name.isEmpty) return null;
    final List<Map<String, Object?>> rows = await db.query(
      'domains',
      columns: <String>['id'],
      where: 'name = ?',
      whereArgs: <Object?>[name],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return rows.first['id'] as int?;
  }

  /// Count the value of the medals of a month again.
  ///
  /// The cap and the diminishing returns belong to the month, so every
  /// medal of the month is counted together, in the order of the ceremony.
  Future<void> recountMonth(String key, RewardsConfig config) async {
    final List<Map<String, Object?>> rows = await db.query(
      'medals',
      where: 'month_key = ?',
      whereArgs: <Object?>[key],
      orderBy: 'awarded_at ASC, id ASC',
    );
    if (rows.isEmpty) return;
    final List<MedalAward> awards = <MedalAward>[];
    for (final Map<String, Object?> row in rows) {
      awards.add(
        MedalAward(
          tier: row['tier']! as String,
          virtue: row['virtue']! as String,
          monthKey: row['month_key']! as String,
          valueRaw: row['value_raw']! as int,
          domainKey: await _domainKeyOf(row['domain_id'] as int?),
          kind: row['kind'] as String? ?? 'earned',
        ),
      );
    }
    final List<int> counted = countAwards(awards, config);
    for (int index = 0; index < rows.length; index++) {
      await db.update(
        'medals',
        <String, Object?>{'value_counted': counted[index]},
        where: 'id = ?',
        whereArgs: <Object?>[rows[index]['id']],
      );
    }
  }

  /// The name of a domain of a medal.
  Future<String?> _domainKeyOf(int? domainId) async {
    if (domainId == null) return null;
    final List<Map<String, Object?>> rows = await db.query(
      'domains',
      columns: <String>['name'],
      where: 'id = ?',
      whereArgs: <Object?>[domainId],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return rows.first['name'] as String?;
  }

  /// Write that a title was reached.
  Future<void> reachTitle(String titleKey, {DateTime? at}) async {
    await db.insert('title_history', <String, Object?>{
      'title_key': titleKey,
      'reached_at': (at ?? DateTime.now().toUtc()).toIso8601String(),
    });
  }
}
