import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../providers/people_providers.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final teachers = ref.watch(teachersProvider);
    final classes = ref.watch(classSectionsProvider);

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Dashboard', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          const Text(
            'The Action Center — a prioritized inbox of one-tap decisions — arrives in '
            'Phase 4. For now: what\'s actually seeded.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 24),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: [
              _StatCard(
                label: 'Teachers',
                value: teachers.whenOrNull(data: (d) => d.length.toString()) ?? '—',
              ),
              _StatCard(
                label: 'Class sections',
                value: classes.whenOrNull(data: (d) => d.length.toString()) ?? '—',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(value, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          ],
        ),
      ),
    );
  }
}
