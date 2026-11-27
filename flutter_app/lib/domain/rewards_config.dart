/// The rules of the reward engine.
///
/// The numbers live in `assets/rewards.yaml` — the very same file the
/// python app reads — and are read when the app starts. A wrong number
/// is reported instead of breaking the app.
library;

import 'package:flutter/services.dart' show rootBundle;
import 'package:yaml/yaml.dart';

/// The tiers of the medals, from the lowest to the highest.
const List<String> kTiers = <String>['bronze', 'silver', 'gold'];

/// The six virtues, in the order the app knows them.
const List<String> kVirtues = <String>[
  'prowess',
  'valor',
  'wisdom',
  'loyalty',
  'largesse',
  'temperance',
];

/// What a medal of a tier needs to be earned.
class EvidenceRule {
  const EvidenceRule({
    required this.tasks,
    required this.impactNote,
    required this.concrete,
  });

  final int tasks;
  final bool impactNote;
  final bool concrete;
}

/// The rules of counting the value of the medals.
class CountingRules {
  const CountingRules({required this.monthlyCap, required this.diminishingFactor});

  final int monthlyCap;
  final double diminishingFactor;
}

/// The rules of the fiefs.
class FiefRules {
  const FiefRules({required this.medalsPerFief});

  final int medalsPerFief;
}

/// The rule of one title of the ladder.
class TitleRule {
  const TitleRule({
    required this.key,
    required this.degrees,
    this.musters,
    this.silver,
    this.gold,
    this.virtues,
    this.virtuesMustInclude = const <String>[],
    this.fiefs,
    this.vigil = false,
  });

  final String key;
  final int degrees;
  final int? musters;
  final int? silver;
  final int? gold;
  final int? virtues;
  final List<String> virtuesMustInclude;
  final int? fiefs;
  final bool vigil;
}

/// The whole configuration of the reward engine.
class RewardsConfig {
  RewardsConfig({
    required this.medalTiers,
    required this.evidence,
    required this.degreeSize,
    required this.counting,
    required this.fiefs,
    required this.titles,
  });

  /// The value of a medal of every tier, before the cap.
  final Map<String, int> medalTiers;

  /// What a medal of every tier needs to be earned.
  final Map<String, EvidenceRule> evidence;

  /// The value that makes one degree.
  final int degreeSize;

  final CountingRules counting;
  final FiefRules fiefs;

  /// The ladder of the titles, from the page at the bottom to the last.
  final List<TitleRule> titles;

  /// The value of a medal of a tier.
  int valueOf(String tier) => medalTiers[tier] ?? 0;

  /// Read the configuration out of the yaml of the assets.
  static Future<RewardsConfig> load() async {
    final String text = await rootBundle.loadString('assets/rewards.yaml');
    return RewardsConfig.fromYaml(loadYaml(text));
  }

  /// Read the configuration out of a yaml document.
  factory RewardsConfig.fromYaml(YamlNode document) {
    final YamlMap map = document as YamlMap;
    final Map<String, int> tiers = <String, int>{};
    final YamlMap tierMap = map['medal_tiers'] as YamlMap;
    for (final String tier in tierMap.keys) {
      tiers[tier] = tierMap[tier] as int;
    }
    final Map<String, EvidenceRule> evidence = <String, EvidenceRule>{};
    final YamlMap evidenceMap = map['evidence'] as YamlMap;
    for (final String tier in evidenceMap.keys) {
      final YamlMap rule = evidenceMap[tier] as YamlMap;
      evidence[tier] = EvidenceRule(
        tasks: rule['tasks'] as int? ?? 0,
        impactNote: rule['impact_note'] as bool? ?? false,
        concrete: rule['concrete'] as bool? ?? false,
      );
    }
    final YamlMap countingMap = map['counting'] as YamlMap;
    final YamlMap fiefMap = map['fiefs'] as YamlMap;
    final List<TitleRule> titles = <TitleRule>[];
    final YamlList titleList = map['titles'] as YamlList;
    for (final Object? entry in titleList) {
      final YamlMap rule = entry as YamlMap;
      titles.add(
        TitleRule(
          key: rule['key'] as String,
          degrees: rule['degrees'] as int? ?? 0,
          musters: rule['musters'] as int?,
          silver: rule['silver'] as int?,
          gold: rule['gold'] as int?,
          virtues: rule['virtues'] as int?,
          virtuesMustInclude:
              (rule['virtues_must_include'] as YamlList?)?.map((Object? e) => e as String).toList() ??
                  const <String>[],
          fiefs: rule['fiefs'] as int?,
          vigil: rule['vigil'] as bool? ?? false,
        ),
      );
    }
    return RewardsConfig(
      medalTiers: tiers,
      evidence: evidence,
      degreeSize: map['degree_size'] as int? ?? 6,
      counting: CountingRules(
        monthlyCap: countingMap['monthly_cap'] as int? ?? 10,
        diminishingFactor: (countingMap['diminishing_factor'] as num?)?.toDouble() ?? 0.5,
      ),
      fiefs: FiefRules(medalsPerFief: fiefMap['medals_per_fief'] as int? ?? 3),
      titles: titles,
    );
  }
}
