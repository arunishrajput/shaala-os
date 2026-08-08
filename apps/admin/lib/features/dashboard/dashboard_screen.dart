import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../providers/briefing_providers.dart';
import '../../providers/people_providers.dart';
import 'action_center.dart';
import 'outbox_panel.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final teachers = ref.watch(teachersProvider);
    final classes = ref.watch(classSectionsProvider);
    final students = ref.watch(studentsCountProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Dashboard', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          const Text(
            'What needs a decision, first.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 20),
          const ActionCenter(),
          const SizedBox(height: 24),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: [
              _StatCard(
                label: 'Students',
                value: students.whenOrNull(data: (d) => d.toString()) ?? '—',
              ),
              _StatCard(
                label: 'Teachers',
                value:
                    teachers.whenOrNull(data: (d) => d.length.toString()) ??
                    '—',
              ),
              _StatCard(
                label: 'Class sections',
                value:
                    classes.whenOrNull(data: (d) => d.length.toString()) ?? '—',
              ),
            ],
          ),
          const SizedBox(height: 24),
          const _BriefingSection(),
          const SizedBox(height: 24),
          const OutboxPanel(),
        ],
      ),
    );
  }
}

/// PROMPT.md §6.6: one button turns computed aggregates into a short
/// narrative. `source` is surfaced rather than hidden -- "written by Gemini"
/// vs "generated locally" is the same honesty the Staffing forecast already
/// practices with its own "forecast, not prophecy" label.
class _BriefingSection extends ConsumerWidget {
  const _BriefingSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(briefingProvider);
    final briefing = state.briefing;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  "Principal's weekly briefing",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: state.loading
                      ? null
                      : () => ref.read(briefingProvider.notifier).generate(),
                  icon: state.loading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.auto_awesome, size: 18),
                  label: Text(briefing == null ? 'Generate' : 'Regenerate'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (state.error != null)
              Text(
                state.error!,
                style: const TextStyle(color: AppColors.critical),
              )
            else if (briefing != null) ...[
              Text(briefing.narrative),
              const SizedBox(height: 8),
              Text(
                briefing.source == 'gemini'
                    ? "Written by Gemini from this week's live numbers."
                    : "Generated locally from this week's live numbers.",
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 12,
                ),
              ),
            ] else
              const Text(
                "One tap turns this week's numbers into a short briefing.",
                style: TextStyle(color: AppColors.textSecondary),
              ),
          ],
        ),
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
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              transitionBuilder: (child, animation) =>
                  FadeTransition(opacity: animation, child: child),
              child: Text(
                value,
                key: ValueKey(value),
                style: Theme.of(context).textTheme.headlineMedium,
              ),
            ),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          ],
        ),
      ),
    );
  }
}
