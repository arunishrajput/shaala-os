import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../providers/timetable_providers.dart';

Future<void> showSubstituteDialog(BuildContext context, WidgetRef ref, int teacherId) async {
  await ref.read(substitutePanelProvider.notifier).open(teacherId);
  if (!context.mounted) return;
  await showDialog<void>(
    context: context,
    builder: (_) => const SubstituteDialog(),
  );
  ref.read(substitutePanelProvider.notifier).close();
}

class SubstituteDialog extends ConsumerWidget {
  const SubstituteDialog({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(substitutePanelProvider);

    return Dialog(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560, maxHeight: 560),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      state.teacherName == null
                          ? 'Assign substitutes'
                          : '${state.teacherName} — absent ${state.date ?? ''}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              const Divider(height: 1),
              const SizedBox(height: 12),
              Flexible(child: _Body(state: state)),
            ],
          ),
        ),
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.state});
  final SubstitutePanelState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (state.loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 40),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (state.error != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Text(state.error!, style: const TextStyle(color: AppColors.critical)),
      );
    }
    if (state.periods.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 40),
        child: Row(
          children: [
            Icon(Icons.check_circle_outline, color: AppColors.info),
            SizedBox(width: 12),
            Text('Every period is covered.'),
          ],
        ),
      );
    }
    return ListView(
      shrinkWrap: true,
      children: [for (final period in state.periods) _PeriodTile(period: period)],
    );
  }
}

class _PeriodTile extends ConsumerWidget {
  const _PeriodTile({required this.period});
  final Map<String, dynamic> period;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final key = '${period['class_id']}:${period['slot_id']}';
    final assigning = ref.watch(substitutePanelProvider).assigningKey == key;
    final candidates = (period['candidates'] as List).cast<Map<String, dynamic>>();

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${period['class']} · ${period['subject']} · ${period['slot']}',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final c in candidates)
                  Tooltip(
                    message: (c['reasons'] as List).cast<String>().join(' · '),
                    child: OutlinedButton(
                      onPressed: assigning
                          ? null
                          : () => ref
                                .read(substitutePanelProvider.notifier)
                                .assign(period, c['teacher_id'] as int),
                      child: Text(c['teacher_name'] as String),
                    ),
                  ),
              ],
            ),
            if (assigning) ...[
              const SizedBox(height: 8),
              const LinearProgressIndicator(),
            ],
          ],
        ),
      ),
    );
  }
}
