import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/time_slot_info.dart';
import '../data/models/timetable_entry.dart';
import '../data/repositories.dart';
import 'core_providers.dart';
import 'people_providers.dart';

final timetableRepositoryProvider = Provider<TimetableRepository>((ref) {
  return TimetableRepository(ref.watch(apiClientProvider));
});

final timeSlotsProvider = FutureProvider<List<TimeSlotInfo>>((ref) {
  return ref.watch(timetableRepositoryProvider).fetchSlots();
});

enum TimetableViewMode { byClass, byTeacher }

final timetableViewModeProvider = StateProvider<TimetableViewMode>(
  (ref) => TimetableViewMode.byClass,
);
final selectedClassIdProvider = StateProvider<int?>((ref) => null);
final selectedTeacherIdProvider = StateProvider<int?>((ref) => null);
final selectedEntryIdProvider = StateProvider<int?>((ref) => null);

// Derived, not imperative: defaults to the first loaded class/teacher until the
// user explicitly picks one. A `ref.listen`-driven side effect here raced with
// widget rebuilds (the dropdown could render before the write landed); a plain
// computed provider can't race because it's re-evaluated synchronously with
// its dependencies.
final effectiveClassIdProvider = Provider.autoDispose<int?>((ref) {
  final explicit = ref.watch(selectedClassIdProvider);
  if (explicit != null) return explicit;
  return ref.watch(classSectionsProvider).valueOrNull?.firstOrNull?.id;
});

final effectiveTeacherIdProvider = Provider.autoDispose<int?>((ref) {
  final explicit = ref.watch(selectedTeacherIdProvider);
  if (explicit != null) return explicit;
  return ref.watch(teachersProvider).valueOrNull?.firstOrNull?.id;
});

final activeTimetableProvider = FutureProvider.autoDispose<ActiveTimetable>((
  ref,
) {
  final mode = ref.watch(timetableViewModeProvider);
  final repo = ref.watch(timetableRepositoryProvider);
  if (mode == TimetableViewMode.byClass) {
    return repo.fetchActive(classId: ref.watch(effectiveClassIdProvider));
  }
  return repo.fetchActive(teacherId: ref.watch(effectiveTeacherIdProvider));
});

final explainProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((
  ref,
) {
  final entryId = ref.watch(selectedEntryIdProvider);
  if (entryId == null) return Future.value(null);
  return ref.watch(timetableRepositoryProvider).explain(entryId);
});

class GenerateState {
  const GenerateState({this.generating = false, this.lastResult});
  final bool generating;
  final Map<String, dynamic>? lastResult;
}

class GenerateNotifier extends Notifier<GenerateState> {
  @override
  GenerateState build() => const GenerateState();

  Future<void> generate() async {
    state = GenerateState(generating: true, lastResult: state.lastResult);
    try {
      final result = await ref.read(timetableRepositoryProvider).generate();
      state = GenerateState(lastResult: result);
    } catch (e) {
      state = GenerateState(
        lastResult: {
          'feasible': false,
          'reasons': [friendlyError(e)],
        },
      );
    }
    ref.invalidate(activeTimetableProvider);
  }
}

final generateProvider = NotifierProvider<GenerateNotifier, GenerateState>(
  GenerateNotifier.new,
);

/// The "mark absent -> assign substitutes" flow (PROMPT.md §6.2 point 3), open
/// across whichever screen triggered it (the Action Center's uncovered_classes
/// card, most often). `periods` uses (class_id, slot_id) as the assignment
/// key, not entry_id -- every successful assignment clones the active
/// timetable version, which would make a stale entry_id from an earlier
/// period in the same batch invalid by the time it's used.
class SubstitutePanelState {
  const SubstitutePanelState({
    this.absenceId,
    this.teacherName,
    this.date,
    this.periods = const [],
    this.loading = false,
    this.error,
    this.assigningKey,
  });

  final int? absenceId;
  final String? teacherName;
  final String? date;
  final List<Map<String, dynamic>> periods;
  final bool loading;
  final String? error;
  final String? assigningKey;

  bool get isOpen => loading || absenceId != null || error != null;
}

class SubstitutePanelNotifier extends Notifier<SubstitutePanelState> {
  @override
  SubstitutePanelState build() => const SubstitutePanelState();

  Future<void> open(int teacherId) async {
    state = const SubstitutePanelState(loading: true);
    try {
      final result = await ref
          .read(timetableRepositoryProvider)
          .markAbsence(teacherId);
      state = SubstitutePanelState(
        absenceId: result['absence_id'] as int,
        teacherName: result['teacher_name'] as String,
        date: result['date'] as String,
        periods: (result['uncovered_periods'] as List)
            .cast<Map<String, dynamic>>(),
      );
    } catch (e) {
      state = SubstitutePanelState(error: friendlyError(e));
    }
  }

  Future<void> assign(
    Map<String, dynamic> period,
    int candidateTeacherId,
  ) async {
    final key = '${period['class_id']}:${period['slot_id']}';
    state = SubstitutePanelState(
      absenceId: state.absenceId,
      teacherName: state.teacherName,
      date: state.date,
      periods: state.periods,
      assigningKey: key,
    );
    try {
      await ref
          .read(timetableRepositoryProvider)
          .assignSubstitute(
            absenceId: state.absenceId!,
            classId: period['class_id'] as int,
            slotId: period['slot_id'] as int,
            teacherId: candidateTeacherId,
          );
      state = SubstitutePanelState(
        absenceId: state.absenceId,
        teacherName: state.teacherName,
        date: state.date,
        periods: [
          for (final p in state.periods)
            if (p['class_id'] != period['class_id'] ||
                p['slot_id'] != period['slot_id'])
              p,
        ],
      );
      ref.invalidate(activeTimetableProvider);
    } catch (e) {
      state = SubstitutePanelState(
        absenceId: state.absenceId,
        teacherName: state.teacherName,
        date: state.date,
        periods: state.periods,
        error: friendlyError(e),
      );
    }
  }

  void close() => state = const SubstitutePanelState();
}

final substitutePanelProvider =
    NotifierProvider<SubstitutePanelNotifier, SubstitutePanelState>(
      SubstitutePanelNotifier.new,
    );
