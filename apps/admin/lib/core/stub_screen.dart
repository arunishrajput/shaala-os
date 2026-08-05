import 'package:flutter/material.dart';

import 'theme.dart';

/// A visible, honest "not built yet" state (CLAUDE.md: stub loudly, never
/// silently). Every nav destination not yet implemented uses this instead of
/// a blank screen or fake data.
class StubScreen extends StatelessWidget {
  const StubScreen({required this.title, required this.phase, super.key});

  final String title;
  final String phase;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.construction_outlined, size: 48, color: AppColors.textSecondary),
          const SizedBox(height: 16),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'Not built yet — arrives in $phase.',
            style: const TextStyle(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
