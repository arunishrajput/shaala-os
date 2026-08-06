import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/attendance_record.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final attendanceRepositoryProvider = Provider<AttendanceRepository>((ref) {
  return AttendanceRepository(ref.watch(apiClientProvider));
});

/// Today's live feed (PROMPT.md §6.4A: "row slides into the live feed,
/// counter ticks up on every connected device"). Self-invalidates on
/// attendance.marked, which every scan/manual mark broadcasts.
class AttendanceTodayNotifier extends AsyncNotifier<AttendanceToday> {
  @override
  Future<AttendanceToday> build() {
    ref.listen(eventStreamProvider, (_, next) {
      if (next.value?.type == 'attendance.marked') ref.invalidateSelf();
    });
    return ref.read(attendanceRepositoryProvider).fetchToday();
  }
}

final attendanceTodayProvider =
    AsyncNotifierProvider<AttendanceTodayNotifier, AttendanceToday>(
      AttendanceTodayNotifier.new,
    );

final selectedRollCallClassIdProvider = StateProvider<int?>((ref) => null);

enum ScanFeedback { none, marked, duplicate, unknown }

class KioskState {
  const KioskState({this.feedback = ScanFeedback.none, this.message});
  final ScanFeedback feedback;
  final String? message;
}

class KioskNotifier extends Notifier<KioskState> {
  @override
  KioskState build() => const KioskState();

  DateTime _lastHandled = DateTime.fromMillisecondsSinceEpoch(0);

  Future<void> handleScan(String qrToken) async {
    // mobile_scanner fires onDetect repeatedly for the same code while it
    // stays in frame; debounce client-side so one card in view doesn't spam
    // requests (the backend already dedupes by day, this is just noise
    // control).
    final now = DateTime.now();
    if (now.difference(_lastHandled) < const Duration(seconds: 2)) return;
    _lastHandled = now;

    final result = await ref.read(attendanceRepositoryProvider).scan(qrToken);
    switch (result['status']) {
      case 'marked':
        state = KioskState(
          feedback: ScanFeedback.marked,
          message: '${result['record']['student_name']} checked in',
        );
      case 'duplicate':
        state = KioskState(
          feedback: ScanFeedback.duplicate,
          message: result['message'] as String?,
        );
      default:
        state = const KioskState(
          feedback: ScanFeedback.unknown,
          message: 'Unregistered card.',
        );
    }
    ref.invalidate(attendanceTodayProvider);
  }
}

final kioskProvider = NotifierProvider<KioskNotifier, KioskState>(KioskNotifier.new);
