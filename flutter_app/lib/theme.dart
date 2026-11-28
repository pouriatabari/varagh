/// The two themes of the app: the night and the parchment.
///
/// The colours are the same tokens the web app uses, so the two look the
/// same on the screen of the desktop and on the screen of the phone.
library;

import 'package:flutter/material.dart';

/// The colours of one theme.
class AppPalette {
  const AppPalette({
    required this.name,
    required this.background,
    required this.elevated,
    required this.sunken,
    required this.text,
    required this.muted,
    required this.border,
    required this.accent,
    required this.accentSoft,
    required this.accentTwo,
    required this.accentTwoSoft,
    required this.danger,
    required this.dangerSoft,
    required this.warn,
    required this.warnSoft,
    required this.info,
    required this.infoSoft,
    required this.gilt,
    required this.iron,
    required this.ink,
    required this.floorOne,
    required this.floorTwo,
    required this.floorThree,
    required this.brightness,
  });

  final String name;
  final Color background;
  final Color elevated;
  final Color sunken;
  final Color text;
  final Color muted;
  final Color border;
  final Color accent;
  final Color accentSoft;
  final Color accentTwo;
  final Color accentTwoSoft;
  final Color danger;
  final Color dangerSoft;
  final Color warn;
  final Color warnSoft;
  final Color info;
  final Color infoSoft;

  /// The gold of the insignia and of the road that is open.
  final Color gilt;

  /// The grey of the iron and of the road that is closed.
  final Color iron;

  /// The colour of the letters of the interface on the dark field.
  final Color ink;

  /// The field the tree of the ranks is drawn on.
  final Color floorOne;
  final Color floorTwo;
  final Color floorThree;

  final Brightness brightness;

  /// The night: the dark of a watchtower with a warm gold.
  static const AppPalette night = AppPalette(
    name: 'night',
    background: Color(0xFF0E1420),
    elevated: Color(0xFF161E2C),
    sunken: Color(0xFF0A0F18),
    text: Color(0xFFE8ECF4),
    muted: Color(0xFF93A1B8),
    border: Color(0xFF26324A),
    accent: Color(0xFFD9B45A),
    accentSoft: Color(0xFF2A2415),
    accentTwo: Color(0xFF5EC8B0),
    accentTwoSoft: Color(0xFF142B28),
    danger: Color(0xFFE08B83),
    dangerSoft: Color(0xFF33201F),
    warn: Color(0xFFE0B56A),
    warnSoft: Color(0xFF322A1A),
    info: Color(0xFF86B4E6),
    infoSoft: Color(0xFF1B2735),
    gilt: Color(0xFFD4A72C),
    iron: Color(0xFF6C7789),
    ink: Color(0xFFE8ECF4),
    floorOne: Color(0xFF1B2534),
    floorTwo: Color(0xFF101722),
    floorThree: Color(0xFF080C13),
    brightness: Brightness.dark,
  );

  /// The parchment: the warm paper of a ledger.
  static const AppPalette parchment = AppPalette(
    name: 'parchment',
    background: Color(0xFFF3E7CD),
    elevated: Color(0xFFFBF3DF),
    sunken: Color(0xFFE7D8B6),
    text: Color(0xFF2C2114),
    muted: Color(0xFF6D5C43),
    border: Color(0xFFD3BD92),
    accent: Color(0xFF9A6F1C),
    accentSoft: Color(0xFFEFE0BB),
    accentTwo: Color(0xFF1F6F5E),
    accentTwoSoft: Color(0xFFD8E6DD),
    danger: Color(0xFFA33C31),
    dangerSoft: Color(0xFFF2D9D2),
    warn: Color(0xFF8A6114),
    warnSoft: Color(0xFFF0E2C2),
    info: Color(0xFF2B5F96),
    infoSoft: Color(0xFFDBE5EF),
    gilt: Color(0xFF9A6F1C),
    iron: Color(0xFF6C7789),
    ink: Color(0xFFF2E7CE),
    floorOne: Color(0xFFF3E9D2),
    floorTwo: Color(0xFFE3D3AE),
    floorThree: Color(0xFFCDB98D),
    brightness: Brightness.light,
  );
}

/// The theme of the app for one palette.
ThemeData buildTheme(AppPalette palette) {
  final ColorScheme scheme = ColorScheme.fromSeed(
    seedColor: palette.accent,
    brightness: palette.brightness,
  ).copyWith(
    primary: palette.accent,
    onPrimary: palette.brightness == Brightness.dark ? const Color(0xFF1A1405) : Colors.white,
    secondary: palette.accentTwo,
    surface: palette.elevated,
    onSurface: palette.text,
    error: palette.danger,
  );

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: palette.background,
    canvasColor: palette.background,
    dividerColor: palette.border,
    // The font of the system is used: it writes Persian well on every
    // platform. The Vazirmatn of the web app may be added as a TTF under
    // assets/fonts and named here when the desktop and the phone need
    // exactly the same letters as the browser.
    textTheme: _textTheme(palette),
    appBarTheme: AppBarTheme(
      backgroundColor: palette.elevated,
      foregroundColor: palette.text,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: palette.elevated,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: palette.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: palette.sunken,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: palette.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: palette.border),
      ),
      labelStyle: TextStyle(color: palette.muted),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: palette.accentSoft,
      labelStyle: TextStyle(color: palette.text, fontSize: 12),
      side: BorderSide(color: palette.border),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    navigationRailTheme: NavigationRailThemeData(
      backgroundColor: palette.elevated,
      indicatorColor: palette.accentSoft,
      selectedIconTheme: IconThemeData(color: palette.accent),
      unselectedIconTheme: IconThemeData(color: palette.muted),
      selectedLabelTextStyle: TextStyle(color: palette.text, fontSize: 12),
      unselectedLabelTextStyle: TextStyle(color: palette.muted, fontSize: 12),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: palette.elevated,
      indicatorColor: palette.accentSoft,
      labelTextStyle: WidgetStatePropertyAll<TextStyle>(TextStyle(color: palette.text, fontSize: 11)),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: palette.elevated,
      contentTextStyle: TextStyle(color: palette.text),
    ),
  );
}

TextTheme _textTheme(AppPalette palette) {
  final TextTheme base = ThemeData(brightness: palette.brightness).textTheme;
  return base.copyWith(
    bodyLarge: base.bodyLarge?.copyWith(color: palette.text),
    bodyMedium: base.bodyMedium?.copyWith(color: palette.text),
    bodySmall: base.bodySmall?.copyWith(color: palette.muted),
    titleLarge: base.titleLarge?.copyWith(color: palette.text),
    titleMedium: base.titleMedium?.copyWith(color: palette.text),
    labelLarge: base.labelLarge?.copyWith(color: palette.text),
  );
}
