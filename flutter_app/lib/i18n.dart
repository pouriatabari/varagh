/// The words of the interface.
///
/// The app speaks Persian and reads from the right to left. The keys are
/// English and neutral; the words below are the ones the user reads.
library;

class Fa {
  const Fa._();

  /// The words of the interface, by key.
  static const Map<String, String> words = <String, String>{
    // The shell.
    'app.name': 'ورق',
    'nav.dashboard': 'داشبورد',
    'nav.tasks': 'کارها',
    'nav.learning': 'یادگیری',
    'nav.reviews': 'ارزیابی‌ها',
    'nav.honours': 'تالار افتخارات',
    'nav.realms': 'نقشهٔ قلمروها',
    'nav.journal': 'دفتر',
    'nav.settings': 'تنظیمات',

    // The hall of honours.
    'honours.title': 'تالار افتخارات',
    'honours.tree_title': 'درختِ رتبه‌ها',
    'honours.tree_hint': 'روی هر نشان بزن تا جزئیاتش را ببینی.',
    'honours.requirements': 'شرط‌ها',
    'honours.rewards': 'دستاوردها',
    'honours.reward_insignia': 'نشانِ این رتبه، با میخ‌های درجه‌هایش',
    'honours.reward_degrees': 'درجه‌های شمرده: {count}',
    'honours.reached': 'باز شده',
    'honours.current': 'رتبهٔ کنونیِ تو',
    'honours.next': 'رتبهٔ بعدی',
    'honours.locked': 'هنوز بسته',
    'honours.met': 'انجام شده',
    'honours.unmet': 'هنوز نیست',
    'honours.requirement_body': 'از {current} تا {required} شمرده شده.',
    'honours.pick_a_node': 'روی یکی از نشان‌ها بزن تا جزئیاتش را ببینی.',
    'honours.legend': 'راهنمای نشان‌ها',
    'honours.legend_open': 'راهِ گشوده',
    'honours.legend_ready': 'راهِ آماده',
    'honours.legend_locked': 'راهِ بسته',
    'honours.legend_current': 'رتبهٔ کنونی',

    // The gates of a title.
    'gate.degrees': 'درجه‌ها',
    'gate.musters': 'سان‌ها',
    'gate.silver': 'نقره',
    'gate.gold': 'زر',
    'gate.virtues': 'فضیلت‌ها',
    'gate.fiefs': 'لردی',
    'gate.vigil': 'شب‌زنداری',

    // The virtues.
    'virtue.prowess': 'توان',
    'virtue.valor': 'دلیری',
    'virtue.wisdom': 'خرد',
    'virtue.loyalty': 'وفاداری',
    'virtue.largesse': 'بخشندگی',
    'virtue.temperance': 'خویشتن‌داری',

    // The titles of the ladder.
    'title.page': 'پیج',
    'title.squire': 'اسکوایر',
    'title.knight': 'شوالیه',
    'title.banneret': 'شوالیه‌ی پرچم‌دار',
    'title.baron': 'بارون',
    'title.viscount': 'ویسکونت',
    'title.earl': 'ارل',
    'title.marquess': 'مارکیز',
    'title.duke': 'دوک',
    'title.prince': 'شاهزاده',
    'title.king': 'پادشاه',
  };

  /// The word of a key, with its placeholders filled in.
  static String t(String key, [Map<String, Object?> values = const <String, Object?>{}]) {
    String word = words[key] ?? key;
    values.forEach((String name, Object? value) {
      word = word.replaceAll('{$name}', '$value');
    });
    return word;
  }

  /// The name of a title of the ladder.
  static String title(String key) => t('title.$key');

  /// The name of a gate.
  static String gate(String key) {
    if (key.startsWith('virtue:')) {
      return virtue(key.split(':').last);
    }
    return t('gate.$key');
  }

  /// The name of a virtue.
  static String virtue(String key) => t('virtue.$key');
}
