import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../providers/people_providers.dart';

class ClassStudentsScreen extends ConsumerWidget {
  const ClassStudentsScreen({required this.classId, this.classLabel, super.key});

  final int classId;
  final String? classLabel;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final students = ref.watch(studentsByClassProvider(classId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => context.go('/people'),
              ),
              Text(
                classLabel ?? 'Class $classId',
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ],
          ),
        ),
        Expanded(
          child: students.when(
            loading: () => const SkeletonList(),
            error: (err, _) => ErrorState(
              message: 'Could not load students: $err',
              onRetry: () => ref.invalidate(studentsByClassProvider(classId)),
            ),
            data: (list) => ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: list.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final s = list[index];
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: AppColors.accent.withValues(alpha: 0.2),
                    child: Text(
                      '${s.rollNo}',
                      style: const TextStyle(color: AppColors.accent, fontSize: 12),
                    ),
                  ),
                  title: Text(s.name),
                  subtitle: Text('Guardian: ${s.guardianName} · ${s.guardianPhone}'),
                  trailing: Text(
                    s.admissionNo,
                    style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}
