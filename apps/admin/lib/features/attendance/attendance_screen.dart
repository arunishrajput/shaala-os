import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:web/web.dart' as web;

import '../../core/env.dart';
import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../data/models/attendance_record.dart';
import '../../data/models/student.dart';
import '../../data/repositories.dart';
import '../../providers/attendance_providers.dart';
import '../../providers/people_providers.dart';

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(
    length: 2,
    vsync: this,
  );

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
          child: Row(
            children: [
              Expanded(
                child: TabBar(
                  controller: _tabController,
                  isScrollable: true,
                  labelColor: AppColors.accent,
                  unselectedLabelColor: AppColors.textSecondary,
                  indicatorColor: AppColors.accent,
                  tabs: const [
                    Tab(text: 'Kiosk'),
                    Tab(text: 'Manual roll call'),
                  ],
                ),
              ),
              OutlinedButton.icon(
                icon: const Icon(Icons.badge_outlined, size: 18),
                label: const Text('Download ID cards'),
                onPressed: () {
                  web.window.open(
                    '${Env.apiBaseUrl}/students/id-cards.pdf',
                    '_blank',
                  );
                },
              ),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [_KioskTab(), _ManualRollCallTab()],
          ),
        ),
      ],
    );
  }
}

class _KioskTab extends ConsumerStatefulWidget {
  const _KioskTab();

  @override
  ConsumerState<_KioskTab> createState() => _KioskTabState();
}

class _KioskTabState extends ConsumerState<_KioskTab> {
  final _controller = MobileScannerController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final todayAsync = ref.watch(attendanceTodayProvider);
    final kiosk = ref.watch(kioskProvider);

    final camera = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: SizedBox(
            height: 320,
            child: MobileScanner(
              controller: _controller,
              onDetect: (capture) {
                final token = capture.barcodes.firstOrNull?.rawValue;
                if (token != null) {
                  ref.read(kioskProvider.notifier).handleScan(token);
                }
              },
              errorBuilder: (context, error, child) => Container(
                color: AppColors.slateMid,
                alignment: Alignment.center,
                padding: const EdgeInsets.all(24),
                child: Text(
                  'Camera unavailable: ${error.errorCode.name}. '
                  'Grant camera access, or use manual roll call.',
                  style: const TextStyle(color: AppColors.textSecondary),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (kiosk.feedback != ScanFeedback.none) _FeedbackBanner(state: kiosk),
      ],
    );

    return Padding(
      padding: const EdgeInsets.all(16),
      child: LayoutBuilder(
        builder: (context, constraints) {
          // Phone-width: the fixed-420px camera pane can't sit beside the
          // feed without overflowing (PROMPT.md §7.2's "responsive down to
          // phone width") -- stack them instead.
          final narrow = constraints.maxWidth < 760;
          final feed = todayAsync.when(
            loading: () => const SkeletonList(),
            error: (err, _) => ErrorState(
              message:
                  'Could not load today\'s attendance: ${friendlyError(err)}',
              onRetry: () => ref.invalidate(attendanceTodayProvider),
            ),
            data: (today) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      '${today.present} / 600',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(width: 8),
                    const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Text(
                        'checked in today',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Expanded(
                  child: today.records.isEmpty
                      ? const Center(
                          child: Text(
                            'No scans yet today.',
                            style: TextStyle(color: AppColors.textSecondary),
                          ),
                        )
                      : ListView.separated(
                          itemCount: today.records.length,
                          separatorBuilder: (_, _) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final r = today.records[index];
                            return ListTile(
                              dense: true,
                              leading: Icon(
                                r.method == 'qr'
                                    ? Icons.qr_code
                                    : Icons.edit_outlined,
                                color: AppColors.textSecondary,
                                size: 18,
                              ),
                              title: Text(r.studentName),
                              trailing: Text(
                                r.status,
                                style: const TextStyle(color: AppColors.info),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          );

          if (narrow) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                camera,
                const SizedBox(height: 16),
                Expanded(child: feed),
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(width: 420, child: camera),
              const SizedBox(width: 24),
              Expanded(child: feed),
            ],
          );
        },
      ),
    );
  }
}

class _FeedbackBanner extends StatelessWidget {
  const _FeedbackBanner({required this.state});
  final KioskState state;

  @override
  Widget build(BuildContext context) {
    final color = switch (state.feedback) {
      ScanFeedback.marked => AppColors.info,
      ScanFeedback.duplicate => AppColors.warning,
      ScanFeedback.unknown => AppColors.critical,
      ScanFeedback.error => AppColors.critical,
      ScanFeedback.none => AppColors.textSecondary,
    };
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(state.message ?? '', style: TextStyle(color: color)),
    );
  }
}

class _ManualRollCallTab extends ConsumerWidget {
  const _ManualRollCallTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final classes = ref.watch(classSectionsProvider);

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          classes.when(
            loading: () => const SizedBox(),
            error: (_, _) => const SizedBox(),
            data: (list) {
              final selected =
                  ref.watch(selectedRollCallClassIdProvider) ??
                  list.firstOrNull?.id;
              return DropdownButton<int>(
                value: selected,
                items: [
                  for (final c in list)
                    DropdownMenuItem(value: c.id, child: Text(c.label)),
                ],
                onChanged: (id) =>
                    ref.read(selectedRollCallClassIdProvider.notifier).state =
                        id,
              );
            },
          ),
          const SizedBox(height: 12),
          Expanded(
            child: Consumer(
              builder: (context, ref, _) {
                final classes = ref.watch(classSectionsProvider).valueOrNull;
                final classId =
                    ref.watch(selectedRollCallClassIdProvider) ??
                    classes?.firstOrNull?.id;
                if (classId == null) {
                  return const Center(
                    child: Text(
                      'No classes seeded yet.',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  );
                }
                final students = ref.watch(studentsByClassProvider(classId));
                return students.when(
                  loading: () => const SkeletonList(),
                  error: (err, _) => ErrorState(
                    message: 'Could not load students: ${friendlyError(err)}',
                  ),
                  data: (list) => list.isEmpty
                      ? const Center(
                          child: Text(
                            'No students in this class.',
                            style: TextStyle(color: AppColors.textSecondary),
                          ),
                        )
                      : ListView.separated(
                          itemCount: list.length,
                          separatorBuilder: (_, _) => const Divider(height: 1),
                          itemBuilder: (context, index) =>
                              _RollCallRow(student: list[index]),
                        ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _RollCallRow extends ConsumerWidget {
  const _RollCallRow({required this.student});
  final Student student;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final today = ref.watch(attendanceTodayProvider).valueOrNull;
    final current = today?.records.cast<AttendanceRecordModel?>().firstWhere(
      (r) => r?.studentId == student.id,
      orElse: () => null,
    );

    Future<void> mark(String status) async {
      try {
        await ref.read(attendanceRepositoryProvider).manual(student.id, status);
        ref.invalidate(attendanceTodayProvider);
      } catch (e) {
        if (!context.mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not mark attendance: ${friendlyError(e)}'),
          ),
        );
      }
    }

    return ListTile(
      dense: true,
      title: Text(student.name),
      subtitle: Text('Roll ${student.rollNo}'),
      trailing: Wrap(
        spacing: 6,
        children: [
          _StatusChip(
            label: 'Present',
            active: current?.status == 'present',
            color: AppColors.info,
            onTap: () => mark('present'),
          ),
          _StatusChip(
            label: 'Late',
            active: current?.status == 'late',
            color: AppColors.warning,
            onTap: () => mark('late'),
          ),
          _StatusChip(
            label: 'Absent',
            active: current?.status == 'absent',
            color: AppColors.critical,
            onTap: () => mark('absent'),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.active,
    required this.color,
    required this.onTap,
  });
  final String label;
  final bool active;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: active,
      selectedColor: color.withValues(alpha: 0.3),
      onSelected: (_) => onTap(),
    );
  }
}
