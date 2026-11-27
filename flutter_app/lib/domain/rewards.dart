/// The reward engine — pure domain logic, a port of the python one.
///
/// Nothing in this file touches the database: every function takes the
/// facts it needs and returns the result. The vocabulary of the medals is
/// neutral English; the words of the interface belong to the i18n.
library;

import 'rewards_config.dart';

/// A medal that is being awarded, before its value is counted.
class MedalAward {
  const MedalAward({
    required this.tier,
    required this.virtue,
    required this.monthKey,
    required this.valueRaw,
    this.domainKey,
    this.kind = 'earned',
  });

  final String tier;
  final String virtue;
  final String monthKey;
  final int valueRaw;
  final String? domainKey;
  final String kind;
}

/// A medal that has already been awarded.
class MedalRecord {
  const MedalRecord({
    required this.tier,
    required this.virtue,
    required this.valueCounted,
    this.monthKey = '',
    this.domainKey,
  });

  final String tier;
  final String virtue;
  final int valueCounted;
  final String monthKey;
  final String? domainKey;
}

/// One gate of a title, and how far the user is from it.
class TitleGate {
  const TitleGate({
    required this.key,
    required this.label,
    required this.required,
    required this.current,
    required this.satisfied,
  });

  final String key;
  final String label;
  final int required;
  final int current;
  final bool satisfied;

  /// How much is still missing.
  int get remaining => (required - current).clamp(0, required);
}

/// Where the user stands with the titles.
class TitleState {
  const TitleState({
    required this.current,
    required this.reached,
    required this.nextTitle,
    required this.nextGates,
    required this.eligible,
    required this.degrees,
    required this.totalValue,
    required this.progressToNextDegree,
    required this.virtues,
    required this.silver,
    required this.gold,
    required this.musters,
    required this.fiefs,
  });

  final String current;
  final List<String> reached;
  final String? nextTitle;
  final List<TitleGate> nextGates;
  final bool eligible;
  final int degrees;
  final int totalValue;
  final double progressToNextDegree;
  final List<String> virtues;
  final int silver;
  final int gold;
  final int musters;
  final int fiefs;
}

/// The value of the counted medals.
int totalValue(List<MedalRecord> medals) =>
    medals.fold<int>(0, (int sum, MedalRecord medal) => sum + medal.valueCounted);

/// The medals that counted for something.
List<MedalRecord> countedMedals(List<MedalRecord> medals) =>
    medals.where((MedalRecord medal) => medal.valueCounted > 0).toList();

/// The degrees the counted value makes.
int degreesOf(int value, RewardsConfig config) =>
    value ~/ (config.degreeSize <= 0 ? 1 : config.degreeSize);

/// The share of the way to the next degree, between 0 and 1.
double progressToNextDegree(int value, RewardsConfig config) {
  if (config.degreeSize <= 0) return 0;
  return (value % config.degreeSize) / config.degreeSize;
}

/// The virtues that have at least one counted medal.
List<String> virtuesOf(List<MedalRecord> medals) {
  final List<String> found = <String>[];
  for (final MedalRecord medal in countedMedals(medals)) {
    if (!found.contains(medal.virtue)) found.add(medal.virtue);
  }
  found.sort();
  return found;
}

/// The number of the counted medals of every tier.
Map<String, int> tierCounts(List<MedalRecord> medals) {
  final Map<String, int> counts = <String, int>{for (final String tier in kTiers) tier: 0};
  for (final MedalRecord medal in countedMedals(medals)) {
    if (counts.containsKey(medal.tier)) counts[medal.tier] = counts[medal.tier]! + 1;
  }
  return counts;
}

/// The number of the domains that became a fief.
int fiefCount(List<MedalRecord> medals, RewardsConfig config) {
  final Map<String, int> perDomain = <String, int>{};
  for (final MedalRecord medal in countedMedals(medals)) {
    final String? domain = medal.domainKey;
    if (domain == null) continue;
    perDomain[domain] = (perDomain[domain] ?? 0) + 1;
  }
  return perDomain.values
      .where((int count) => count >= config.fiefs.medalsPerFief)
      .length;
}

/// Count the value of the medals of a month.
///
/// The order of the awards is the order of the ceremony. The second medal
/// of a domain in the same month counts for half, and the month counts for
/// no more than the cap.
List<int> countAwards(List<MedalAward> awards, RewardsConfig config) {
  final List<int> counted = <int>[];
  int used = 0;
  String month = '';
  Map<String, int> seenInDomain = <String, int>{};
  for (final MedalAward award in awards) {
    if (award.monthKey != month) {
      month = award.monthKey;
      used = 0;
      seenInDomain = <String, int>{};
    }
    int value = award.valueRaw;
    final String? domain = award.domainKey;
    if (domain != null) {
      final int seen = seenInDomain[domain] ?? 0;
      seenInDomain[domain] = seen + 1;
      if (seen >= 1) {
        value = (value * config.counting.diminishingFactor).floor();
      }
    }
    final int room = (config.counting.monthlyCap - used).clamp(0, config.counting.monthlyCap);
    final int countedValue = value < room ? value : room;
    used += countedValue;
    counted.add(countedValue);
  }
  return counted;
}

/// The gates of one title, each with the distance that is left.
List<TitleGate> gatesForRule(
  TitleRule rule, {
  required int degreesHeld,
  required int musters,
  required Map<String, int> counts,
  required List<String> virtues,
  required int fiefs,
  required bool vigilDone,
}) {
  final List<TitleGate> gates = <TitleGate>[];
  gates.add(
    TitleGate(
      key: 'degrees',
      label: 'degrees',
      required: rule.degrees,
      current: degreesHeld,
      satisfied: degreesHeld >= rule.degrees,
    ),
  );
  if (rule.musters != null) {
    gates.add(
      TitleGate(
        key: 'musters',
        label: 'musters',
        required: rule.musters!,
        current: musters,
        satisfied: musters >= rule.musters!,
      ),
    );
  }
  if (rule.silver != null) {
    gates.add(
      TitleGate(
        key: 'silver',
        label: 'silver',
        required: rule.silver!,
        current: counts['silver'] ?? 0,
        satisfied: (counts['silver'] ?? 0) >= rule.silver!,
      ),
    );
  }
  if (rule.gold != null) {
    gates.add(
      TitleGate(
        key: 'gold',
        label: 'gold',
        required: rule.gold!,
        current: counts['gold'] ?? 0,
        satisfied: (counts['gold'] ?? 0) >= rule.gold!,
      ),
    );
  }
  if (rule.virtues != null) {
    gates.add(
      TitleGate(
        key: 'virtues',
        label: 'virtues',
        required: rule.virtues!,
        current: virtues.length,
        satisfied: virtues.length >= rule.virtues!,
      ),
    );
  }
  for (final String name in rule.virtuesMustInclude) {
    gates.add(
      TitleGate(
        key: 'virtue:$name',
        label: name,
        required: 1,
        current: virtues.contains(name) ? 1 : 0,
        satisfied: virtues.contains(name),
      ),
    );
  }
  if (rule.fiefs != null) {
    gates.add(
      TitleGate(
        key: 'fiefs',
        label: 'fiefs',
        required: rule.fiefs!,
        current: fiefs,
        satisfied: fiefs >= rule.fiefs!,
      ),
    );
  }
  if (rule.vigil) {
    gates.add(
      TitleGate(
        key: 'vigil',
        label: 'vigil',
        required: 1,
        current: vigilDone ? 1 : 0,
        satisfied: vigilDone,
      ),
    );
  }
  return gates;
}

/// Where the user stands with the titles.
///
/// A title that is only eligible is not reached yet, and no title is ever
/// lost.
TitleState titleState({
  required List<MedalRecord> medals,
  required int musters,
  List<String> reachedTitles = const <String>[],
  int fiefs = 0,
  required RewardsConfig config,
}) {
  final int value = totalValue(medals);
  final int degreesHeld = degreesOf(value, config);
  final Map<String, int> counts = tierCounts(medals);
  final List<String> virtues = virtuesOf(medals);
  final List<String> reached = List<String>.of(reachedTitles);
  final String base = config.titles.isEmpty ? 'page' : config.titles.first.key;
  final Set<String> reachedSet = <String>{...reached, base};

  String current = base;
  for (final TitleRule rule in config.titles) {
    if (reachedSet.contains(rule.key)) current = rule.key;
  }

  TitleRule? nextRule;
  for (final TitleRule rule in config.titles) {
    if (reachedSet.contains(rule.key)) continue;
    nextRule = rule;
    break;
  }

  List<TitleGate> gates = <TitleGate>[];
  bool eligible = false;
  if (nextRule != null) {
    gates = gatesForRule(
      nextRule,
      degreesHeld: degreesHeld,
      musters: musters,
      counts: counts,
      virtues: virtues,
      fiefs: fiefs,
      // The vigil is the ceremony itself: the user becomes eligible when
      // every other gate is met, and the vigil comes with the promotion.
      vigilDone: reachedSet.contains(nextRule.key),
    );
    eligible = gates
        .where((TitleGate gate) => gate.key != 'vigil')
        .every((TitleGate gate) => gate.satisfied);
  }

  return TitleState(
    current: current,
    reached: reached,
    nextTitle: nextRule?.key,
    nextGates: gates,
    eligible: eligible,
    degrees: degreesHeld,
    totalValue: value,
    progressToNextDegree: progressToNextDegree(value, config),
    virtues: virtues,
    silver: counts['silver'] ?? 0,
    gold: counts['gold'] ?? 0,
    musters: musters,
    fiefs: fiefs,
  );
}

/// The gates of one title, with the distance that is left to each.
List<TitleGate> gatesForTitle(
  TitleRule rule, {
  required List<MedalRecord> medals,
  required int musters,
  List<String> reachedTitles = const <String>[],
  int fiefs = 0,
  required RewardsConfig config,
}) {
  return gatesForRule(
    rule,
    degreesHeld: degreesOf(totalValue(medals), config),
    musters: musters,
    counts: tierCounts(medals),
    virtues: virtuesOf(medals),
    fiefs: fiefs,
    vigilDone: reachedTitles.contains(rule.key),
  );
}

/// The title of the list that is the highest of the reached ones.
String highestReachedTitle(List<String> reachedTitles, RewardsConfig config) {
  final List<String> keys = config.titles.map((TitleRule rule) => rule.key).toList();
  String best = keys.isEmpty ? 'page' : keys.first;
  for (final String key in reachedTitles) {
    if (keys.contains(key) && keys.indexOf(key) > keys.indexOf(best)) best = key;
  }
  return best;
}

/// The tier the evidence of a medal really earns.
///
/// A tier may be lowered freely; it may not be raised above what the
/// evidence proves.
String clampedTier(
  String tier, {
  required int taskCount,
  required bool hasImpactNote,
  required bool concrete,
  required RewardsConfig config,
}) {
  final List<String> order = kTiers.where((String name) => config.evidence.containsKey(name)).toList();
  for (final String candidate in order.reversed) {
    final EvidenceRule? rule = config.evidence[candidate];
    if (rule == null) continue;
    if (taskCount < rule.tasks) continue;
    if (rule.impactNote && !hasImpactNote) continue;
    if (rule.concrete && !concrete) continue;
    return candidate;
  }
  return order.isEmpty ? 'bronze' : order.first;
}

/// The rank of a tier: the lowest is 0.
int tierOrder(String tier) {
  final int index = kTiers.indexOf(tier);
  return index < 0 ? 0 : index;
}
