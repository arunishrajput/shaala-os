import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// PROMPT.md §7.1: deep slate base, one accent, semantic severity colors.
// Never default Material blue.
class AppColors {
  static const slateDark = Color(0xFF0F172A);
  static const slateMid = Color(0xFF1E293B);
  static const slateLight = Color(0xFF334155);
  static const accent = Color(0xFF6366F1);
  static const critical = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);
  static const info = Color(0xFF10B981);
  static const textPrimary = Color(0xFFF1F5F9);
  static const textSecondary = Color(0xFF94A3B8);
}

ThemeData buildAppTheme() {
  final base = ThemeData.dark(useMaterial3: true);
  final textTheme = GoogleFonts.plusJakartaSansTextTheme(base.textTheme).apply(
    bodyColor: AppColors.textPrimary,
    displayColor: AppColors.textPrimary,
  );

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.slateDark,
    colorScheme: const ColorScheme.dark(
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
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
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
