import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// PROMPT.md §7.1: one accent, semantic severity colors, never default
// Material blue. Palette is a school exercise book read in morning light --
// a pale sky-blue wash, crisp white "page" cards, rule-blue borders, deep
// ink-navy text -- rather than a generic SaaS pastel. Field names kept as
// slateDark/Mid/Light (their original dark-theme roles: page bg / card
// surface / border) so every call site across the app needed zero changes.
class AppColors {
  static const slateDark = Color(0xFFEAF1FB); // page wash
  static const slateMid = Color(0xFFFFFFFF); // card / surface
  static const slateLight = Color(0xFFC9DCF5); // rule-blue border
  static const accent = Color(0xFF6366F1);
  static const critical = Color(0xFFDC2626);
  static const warning = Color(0xFFB45309);
  static const info = Color(0xFF047857);
  static const textPrimary = Color(0xFF16233F);
  static const textSecondary = Color(0xFF5B6B85);
}

ThemeData buildAppTheme() {
  final base = ThemeData.light(useMaterial3: true);
  final bodyTheme = GoogleFonts.plusJakartaSansTextTheme(base.textTheme).apply(
    bodyColor: AppColors.textPrimary,
    displayColor: AppColors.textPrimary,
  );

  // Fraunces carries the product's own thesis -- paper records becoming
  // data -- into every screen title and headline number: a serif with the
  // weight of an official register, set only where it can breathe (titles,
  // big numbers), never in dense UI chrome or data tables where Plus
  // Jakarta Sans's neutrality keeps things legible.
  TextStyle display(TextStyle? s) =>
      GoogleFonts.fraunces(textStyle: s, fontWeight: FontWeight.w600);

  final textTheme = bodyTheme.copyWith(
    displayLarge: display(bodyTheme.displayLarge),
    displayMedium: display(bodyTheme.displayMedium),
    displaySmall: display(bodyTheme.displaySmall),
    headlineLarge: display(bodyTheme.headlineLarge),
    headlineMedium: display(bodyTheme.headlineMedium),
    headlineSmall: display(bodyTheme.headlineSmall),
  );

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.slateDark,
    colorScheme: const ColorScheme.light(
      primary: AppColors.accent,
      secondary: AppColors.accent,
      surface: AppColors.slateMid,
      error: AppColors.critical,
    ),
    textTheme: textTheme,
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.slateDark,
      elevation: 0,
      foregroundColor: AppColors.textPrimary,
    ),
    cardTheme: CardThemeData(
      color: AppColors.slateMid,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        // White cards on a light wash need a firmer border than the old
        // dark theme did to still read as a distinct "page" edge.
        side: BorderSide(color: AppColors.slateLight.withValues(alpha: 0.9)),
      ),
    ),
    navigationRailTheme: const NavigationRailThemeData(
      backgroundColor: AppColors.slateMid,
      selectedIconTheme: IconThemeData(color: AppColors.accent),
      selectedLabelTextStyle: TextStyle(color: AppColors.accent),
      unselectedIconTheme: IconThemeData(color: AppColors.textSecondary),
      unselectedLabelTextStyle: TextStyle(color: AppColors.textSecondary),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.accent,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
    ),
  );
}
