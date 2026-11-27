/// The reward engine of the Flutter app — the same rules as the python
/// one, and the same numbers.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:varagh/domain/rewards.dart';
import 'package:varagh/domain/rewards_config.dart';

/// The configuration of the app, read from the asset of the repository.
Future<RewardsConfig> configOfAsset() => RewardsConfig.load();

/// A medal that is being awarded.
MedalAward award(
  RewardsConfig config,
  String tier, {
  String? domain,
  String virtue = 'prowess',
  String month = '1404/01',
}) {
  return MedalAward(
    tier: tier,
    virtue: virtue,
    monthKey: month,
    valueRaw: config.valueOf(tier),
    domainKey: domain,
  );
}

/// A medal that has already been awarded.
MedalRecord record(
  RewardsConfig config,
  String tier, {
  String virtue = 'prowess',
  int? value,
  String? domain,
}) {
  return MedalRecord(
    tier: tier,
    virtue: virtue,
    valueCounted: value ?? config.valueOf(tier),
    domainKey: domain,
  );
}

void main() {
  late RewardsConfig config;

  setUpAll(() async {
    config = await configOfAsset();
  });

  group('the tiers and the degrees', () {
    test('the tiers have their value', () {
      expect(config.valueOf('bronze'), 1);
      expect(config.valueOf('silver'), 2);
      expect(config.valueOf('gold'), 4);
    });

    test('the degrees come from the counted value', () {
      expect(degreesOf(0, config), 0);
      expect(degreesOf(5, config), 0);
      expect(degreesOf(6, config), 1);
      expect(degreesOf(11, config), 1);
      expect(degreesOf(12, config), 2);
    });

    test('the progress to the next degree is a share', () {
      expect(progressToNextDegree(0, config), 0.0);
      expect(progressToNextDegree(3, config), closeTo(0.5, 0.0001));
      expect(progressToNextDegree(6, config), closeTo(0.0, 0.0001));
    });
  });

  group('the cap and the diminishing', () {
    test('the month counts at most the cap', () {
      final List<MedalAward> awards = <MedalAward>[
        for (int index = 0; index < 5; index++)
          award(config, 'gold', domain: 'domain-$index'),
      ];
      final List<int> counted = countAwards(awards, config);
      expect(counted, <int>[4, 4, 2, 0, 0]);
      expect(counted.fold<int>(0, (int sum, int value) => sum + value), 10);
    });

    test('the second medal of a domain counts for half', () {
      final List<MedalAward> awards = <MedalAward>[
        award(config, 'silver', domain: 'one', virtue: 'prowess'),
        award(config, 'silver', domain: 'one', virtue: 'valor'),
        award(config, 'silver', domain: 'two', virtue: 'wisdom'),
      ];
      expect(countAwards(awards, config), <int>[2, 1, 2]);
    });

    test('a medal without a domain is never diminished', () {
      final List<MedalAward> awards = <MedalAward>[
        award(config, 'bronze', virtue: 'temperance'),
        award(config, 'bronze', virtue: 'temperance'),
      ];
      expect(countAwards(awards, config), <int>[1, 1]);
    });

    test('the cap starts again in the next month', () {
      final List<MedalAward> awards = <MedalAward>[
        for (int index = 0; index < 4; index++)
          award(config, 'gold', domain: 'd$index', month: '1404/01'),
        for (int index = 0; index < 4; index++)
          award(config, 'gold', domain: 'e$index', month: '1404/02'),
      ];
      final List<int> counted = countAwards(awards, config);
      expect(counted.sublist(0, 4), <int>[4, 4, 2, 0]);
      expect(counted.sublist(4), <int>[4, 4, 2, 0]);
    });
  });

  group('the titles', () {
    test('the title needs its gates', () {
      final TitleRule squire = config.titles
          .firstWhere((TitleRule rule) => rule.key == 'squire');
      final List<TitleGate> gates = gatesForTitle(
        squire,
        medals: <MedalRecord>[],
        musters: 0,
        config: config,
      );
      final Map<String, TitleGate> byKey = <String, TitleGate>{
        for (final TitleGate gate in gates) gate.key: gate,
      };
      expect(byKey.containsKey('degrees'), isTrue);
      expect(byKey.containsKey('musters'), isTrue);
      expect(byKey['degrees']!.satisfied, isFalse);
      expect(byKey['musters']!.satisfied, isFalse);
    });

    test('a reached title is never lost', () {
      final TitleState state = titleState(
        medals: <MedalRecord>[],
        musters: 0,
        reachedTitles: <String>['squire'],
        config: config,
      );
      expect(state.reached, contains('squire'));
      expect(state.current, 'squire');
    });

    test('the king is not reachable before the thirty-ninth month', () {
      final List<MedalRecord> medals = <MedalRecord>[
        for (int index = 0; index < 39; index++) record(config, 'gold'),
      ];
      final TitleState state = titleState(
        medals: medals,
        musters: 0,
        config: config,
      );
      expect(state.current, isNot('king'));
    });

    test('the king needs the gold and the virtues and the fiefs', () {
      final TitleRule king = config.titles
          .firstWhere((TitleRule rule) => rule.key == 'king');
      expect(king.gold, 14);
      expect(king.virtues, 6);
      expect(king.fiefs, 4);
    });
  });

  group('the fiefs', () {
    test('the fiefs come from the medals of a domain', () {
      final List<MedalRecord> medals = <MedalRecord>[
        record(config, 'bronze', domain: 'one'),
        record(config, 'bronze', domain: 'one'),
        record(config, 'bronze', domain: 'one'),
        record(config, 'bronze', domain: 'two'),
      ];
      expect(fiefCount(medals, config), 1);
    });
  });
}
