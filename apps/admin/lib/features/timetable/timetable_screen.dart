import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme.dart';
import '../../data/models/class_section.dart';
import '../../data/models/teacher.dart';
import '../../providers/people_providers.dart';
import '../../providers/timetable_providers.dart';
import 'explain_panel.dart';
import 'timetable_grid.dart';

class TimetableScreen extends ConsumerWidget {
  const TimetableScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedEntryId = ref.watch(selectedEntryIdProvider);
    final grid = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        _Header(),
        Expanded(
          child: Padding(padding: EdgeInsets.all(16), child: TimetableGrid()),
        ),
      ],
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        // Phone-width: the fixed-360px explain panel can't sit beside the
        // grid without overflowing (PROMPT.md §7.2's "responsive down to
        // phone width") -- the grid itself already scrolls horizontally on
        // its own, this is only about the panel joining it.
        final narrow = constraints.maxWidth < 900;
        if (narrow) {
          return selectedEntryId != null
              ? const ExplainPanel(fullWidth: true)
              : grid;
        }
        return Row(
          children: [
            Expanded(child: grid),
            if (selectedEntryId != null) const ExplainPanel(),
          ],
        );
      },
    );
  }
}

class _Header extends ConsumerWidget {
  const _Header();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final generateState = ref.watch(generateProvider);
    final mode = ref.watch(timetableViewModeProvider);
    final classesAsync = ref.watch(classSectionsProvider);
    final teachersAsync = ref.watch(teachersProvider);

    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'Timetable',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Spacer(),
              // Export PDF — fetches bytes via Dio (auth header attached) and
              // triggers a browser download. Disabled while a generate or
              // export is already in flight to prevent duplicate requests.
              const _ExportButton(),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                onPressed: generateState.generating
                    ? null
                    : () => ref.read(generateProvider.notifier).generate(),
                icon: generateState.generating
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.auto_awesome, size: 18),
                label: Text(generateState.generating ? 'Solving…' : 'Generate'),
              ),
            ],
          ),
          if (generateState.lastResult != null)
            _StatsBanner(result: generateState.lastResult!),
          const SizedBox(height: 16),
          Row(
            children: [
              SegmentedButton<TimetableViewMode>(
                segments: const [
                  ButtonSegment(
                    value: TimetableViewMode.byClass,
                    label: Text('By Class'),
                  ),
                  ButtonSegment(
                    value: TimetableViewMode.byTeacher,
                    label: Text('By Teacher'),
                  ),
                ],
                selected: {mode},
                onSelectionChanged: (s) =>
                    ref.read(timetableViewModeProvider.notifier).state =
                        s.first,
              ),
              const SizedBox(width: 16),
              if (mode == TimetableViewMode.byClass)
                classesAsync.when(
                  loading: () => const SizedBox(),
                  error: (_, _) => const SizedBox(),
                  data: (classes) => _ClassDropdown(classes: classes),
                )
              else
                teachersAsync.when(
                  loading: () => const SizedBox(),
                  error: (_, _) => const SizedBox(),
                  data: (teachers) => _TeacherDropdown(teachers: teachers),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ExportButton extends ConsumerWidget {
  const _ExportButton();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final exportState = ref.watch(exportProvider);
    final mode = ref.watch(timetableViewModeProvider);
    final classId = ref.watch(effectiveClassIdProvider);
    final teacherId = ref.watch(effectiveTeacherIdProvider);

    // Surface export errors as a SnackBar and clear the error state so the
    // button re-enables. Using ref.listen rather than checking inside build
    // avoids setState-during-build issues.
    ref.listen(exportProvider, (_, next) {
      if (next.error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.error!),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
        // Reset so the button doesn't stay permanently disabled
        ref.read(exportProvider.notifier).state = const ExportState();
      }
    });

    return OutlinedButton.icon(
      onPressed: exportState.exporting
          ? null
          : () => ref.read(exportProvider.notifier).export(
                view: mode == TimetableViewMode.byClass ? 'class' : 'teacher',
                classId: mode == TimetableViewMode.byClass ? classId : null,
                teacherId:
                    mode == TimetableViewMode.byTeacher ? teacherId : null,
              ),
      icon: exportState.exporting
          ? const SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.picture_as_pdf_outlined, size: 18),
      label: Text(exportState.exporting ? 'Exporting…' : 'Export PDF'),
    );
  }
}

class _ClassDropdown extends ConsumerWidget {
  const _ClassDropdown({required this.classes});
  final List<ClassSection> classes;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(effectiveClassIdProvider);
    return DropdownButton<int>(
      value: selected,
      hint: const Text('Choose a class'),
      items: [
        for (final c in classes)
          DropdownMenuItem(value: c.id, child: Text(c.label)),
      ],
      onChanged: (id) => ref.read(selectedClassIdProvider.notifier).state = id,
    );
  }
}

class _TeacherDropdown extends ConsumerWidget {
  const _TeacherDropdown({required this.teachers});
  final List<Teacher> teachers;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selected = ref.watch(effectiveTeacherIdProvider);
    return DropdownButton<int>(
      value: selected,
      hint: const Text('Choose a teacher'),
      items: [
        for (final t in teachers)
          DropdownMenuItem(value: t.id, child: Text(t.name)),
      ],
      onChanged: (id) =>
          ref.read(selectedTeacherIdProvider.notifier).state = id,
    );
  }
}

class _StatsBanner extends StatelessWidget {
  const _StatsBanner({required this.result});
  final Map<String, dynamic> result;

  @override
  Widget build(BuildContext context) {
    final feasible = result['feasible'] == true;
    final stats = result['stats'] as Map<String, dynamic>?;

    final message = feasible && stats != null
        ? '${stats['total_entries']} assignments across the school in '
              '${stats['wall_time_s']}s, zero hard violations.'
        : ((result['reasons'] as List?)?.cast<String>().join(' ') ??
              'Could not generate.');

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: (feasible ? AppColors.info : AppColors.critical).withValues(
          alpha: 0.15,
        ),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            feasible ? Icons.check_circle_outline : Icons.error_outline,
            color: feasible ? AppColors.info : AppColors.critical,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }
}
