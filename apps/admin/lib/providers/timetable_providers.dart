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

final activeTimetableProvider = FutureProvider.autoDispose<ActiveTimetable>((ref) {
  final mode = ref.watch(timetableViewModeProvider);
  final repo = ref.watch(timetableRepositoryProvider);
  if (mode == TimetableViewMode.byClass) {
    return repo.fetchActive(classId: ref.watch(effectiveClassIdProvider));
  }
  return repo.fetchActive(teacherId: ref.watch(effectiveTeacherIdProvider));
});

final explainProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((ref) {
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
        lastResult: {'feasible': false, 'reasons': ['$e']},
      );
    }
    ref.invalidate(activeTimetableProvider);
  }
}

final generateProvider = NotifierProvider<GenerateNotifier, GenerateState>(GenerateNotifier.new);
