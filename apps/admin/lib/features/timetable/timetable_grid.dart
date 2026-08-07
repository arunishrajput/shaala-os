import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/skeleton.dart';
import '../../core/theme.dart';
import '../../data/models/time_slot_info.dart';
import '../../data/models/timetable_entry.dart';
import '../../data/repositories.dart';
import '../../providers/timetable_providers.dart';

const _dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const _rowHeight = 68.0;

class TimetableGrid extends ConsumerWidget {
  const TimetableGrid({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final slotsAsync = ref.watch(timeSlotsProvider);
    final timetableAsync = ref.watch(activeTimetableProvider);
    final mode = ref.watch(timetableViewModeProvider);

    return slotsAsync.when(
      loading: () => const SkeletonList(),
      error: (err, _) =>
          ErrorState(message: 'Could not load slots: ${friendlyError(err)}'),
      data: (slots) => timetableAsync.when(
        loading: () => const SkeletonList(),
        error: (err, _) => ErrorState(
          message: 'Could not load timetable: ${friendlyError(err)}',
          onRetry: () => ref.invalidate(activeTimetableProvider),
        ),
        data: (timetable) =>
            _Grid(slots: slots, entries: timetable.entries, mode: mode),
      ),
    );
  }
}

class _Grid extends StatelessWidget {
  const _Grid({required this.slots, required this.entries, required this.mode});
  final List<TimeSlotInfo> slots;
  final List<TimetableEntry> entries;
  final TimetableViewMode mode;

  @override
  Widget build(BuildContext context) {
    final periods = slots.map((s) => s.period).toSet().toList()..sort();
    final slotByDayPeriod = {for (final s in slots) '${s.day}_${s.period}': s};
    final entryBySlot = {for (final e in entries) e.slotId: e};

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SingleChildScrollView(
        child: Table(
          border: TableBorder.all(color: AppColors.slateLight, width: 0.5),
          columnWidths: {
            0: const FixedColumnWidth(50),
            for (var i = 1; i <= 6; i++) i: const FixedColumnWidth(150),
          },
          children: [
            TableRow(
              decoration: const BoxDecoration(color: AppColors.slateMid),
              children: [
                const SizedBox(height: 40),
                for (final d in _dayNames)
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(8),
                      child: Text(
                        d,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
              ],
            ),
            for (final p in periods)
              TableRow(
                children: [
                  Center(
                    child: Text(
                      'P$p',
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                  ),
                  for (var day = 0; day < 6; day++)
                    _Cell(
                      slot: slotByDayPeriod['${day}_$p'],
                      entry: () {
                        final s = slotByDayPeriod['${day}_$p'];
                        return s == null ? null : entryBySlot[s.id];
                      }(),
                      mode: mode,
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _Cell extends ConsumerWidget {
  const _Cell({required this.slot, required this.entry, required this.mode});
  final TimeSlotInfo? slot;
  final TimetableEntry? entry;
  final TimetableViewMode mode;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (slot == null) {
      return const SizedBox(height: _rowHeight);
    }
    final targetSlot = slot!;

    return DragTarget<TimetableEntry>(
      onWillAcceptWithDetails: (details) => details.data.id != entry?.id,
      onAcceptWithDetails: (details) =>
          _handleDrop(context, ref, details.data, targetSlot),
      builder: (context, candidateData, rejectedData) {
        final highlight = candidateData.isNotEmpty;
        final content = entry == null
            ? const SizedBox(height: _rowHeight)
            : _EntryChip(entry: entry!, mode: mode);

        return Container(
          height: _rowHeight,
          color: highlight ? AppColors.accent.withValues(alpha: 0.15) : null,
          child: entry == null
              ? content
              : Draggable<TimetableEntry>(
                  data: entry,
                  feedback: Material(
                    color: Colors.transparent,
                    child: SizedBox(
                      width: 150,
                      child: _EntryChip(entry: entry!, mode: mode),
                    ),
                  ),
                  childWhenDragging: Opacity(opacity: 0.3, child: content),
                  child: GestureDetector(
                    onTap: () =>
                        ref.read(selectedEntryIdProvider.notifier).state =
                            entry!.id,
                    child: content,
                  ),
                ),
        );
      },
    );
  }

  Future<void> _handleDrop(
    BuildContext context,
    WidgetRef ref,
    TimetableEntry dragged,
    TimeSlotInfo targetSlot,
  ) async {
    final repo = ref.read(timetableRepositoryProvider);
    final validation = await repo.validateMove(
      dragged.id,
      dragged.roomId,
      targetSlot.id,
    );
    if (validation['ok'] == true) {
      await repo.move(dragged.id, dragged.roomId, targetSlot.id);
      ref.invalidate(activeTimetableProvider);
      return;
    }
    if (!context.mounted) return;
    final conflicts = (validation['conflicts'] as List).cast<String>().join(
      ' ',
    );
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: AppColors.critical,
        content: Text("Can't move there — $conflicts"),
      ),
    );
  }
}

class _EntryChip extends StatelessWidget {
  const _EntryChip({required this.entry, required this.mode});
  final TimetableEntry entry;
  final TimetableViewMode mode;

  @override
  Widget build(BuildContext context) {
    final subtitle = mode == TimetableViewMode.byClass
        ? entry.teacherName
        : entry.classLabel;
    return Container(
      margin: const EdgeInsets.all(2),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: entry.isSubstitution
            ? AppColors.warning.withValues(alpha: 0.25)
            : AppColors.accent.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            entry.subjectName,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
