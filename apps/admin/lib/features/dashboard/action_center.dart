import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme.dart';
import '../../data/models/action_item.dart';
import '../../providers/actions_providers.dart';
import '../../providers/timetable_providers.dart';

Color _severityColor(String severity) {
  switch (severity) {
    case 'critical':
      return AppColors.critical;
    case 'warning':
      return AppColors.warning;
    default:
      return AppColors.info;
  }
}

/// Screens that already exist for a given signal kind to hand off to. The two
/// kinds with a genuinely bespoke flow (uncovered_classes -> assign
/// substitutes, low_attendance_trend -> draft parent messages) are wired in a
/// later commit; until then their primary action is an honest one-tap
/// resolve rather than a fake button.
void _handlePrimaryAction(BuildContext context, WidgetRef ref, ActionItemModel item) {
  switch (item.kind) {
    case 'documents_need_review':
      context.go('/documents');
    case 'staffing_shortfall':
      context.go('/staffing');
    case 'room_conflict':
      context.go('/timetable');
    case 'free_periods':
      final classId = item.payload['class_id'];
      if (classId is int) {
        ref.read(selectedClassIdProvider.notifier).state = classId;
      }
      context.go('/timetable');
    default:
      ref.read(actionItemsProvider.notifier).resolve(item.id);
  }
}

class ActionCenter extends ConsumerWidget {
  const ActionCenter({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final actionsAsync = ref.watch(actionItemsProvider);

    return actionsAsync.when(
      loading: () => const _SkeletonStack(),
      error: (err, _) => Text('$err', style: const TextStyle(color: AppColors.critical)),
      data: (items) {
        if (items.isEmpty) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_outline, color: AppColors.info),
                  const SizedBox(width: 12),
                  Text(
                    'Nothing needs attention right now.',
                    style: TextStyle(color: AppColors.textSecondary),
                  ),
                ],
              ),
            ),
          );
        }
        return Column(
          children: [for (final item in items) _ActionCard(item: item)],
        );
      },
    );
  }
}

class _ActionCard extends ConsumerWidget {
  const _ActionCard({required this.item});
  final ActionItemModel item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AnimatedSize(
      duration: const Duration(milliseconds: 250),
      child: Card(
        margin: const EdgeInsets.only(bottom: 12),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _severityColor(item.severity),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(
                      item.body,
                      style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              TextButton(
                onPressed: () => _handlePrimaryAction(context, ref, item),
                child: Text(item.primaryAction),
              ),
              IconButton(
                tooltip: 'Dismiss',
                icon: const Icon(Icons.close, size: 18, color: AppColors.textSecondary),
                onPressed: () => ref.read(actionItemsProvider.notifier).dismiss(item.id),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SkeletonStack extends StatelessWidget {
  const _SkeletonStack();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < 2; i++)
          Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Container(
              height: 64,
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Container(
                    width: 180,
                    height: 14,
                    color: AppColors.slateLight,
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
