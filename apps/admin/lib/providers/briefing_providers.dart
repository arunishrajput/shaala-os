import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/briefing.dart';
import '../data/repositories.dart';
import 'core_providers.dart';

final briefingRepositoryProvider = Provider<BriefingRepository>((ref) {
  return BriefingRepository(ref.watch(apiClientProvider));
});

class BriefingState {
  const BriefingState({this.loading = false, this.briefing, this.error});
  final bool loading;
  final Briefing? briefing;
  final String? error;
}

class BriefingNotifier extends Notifier<BriefingState> {
  @override
  BriefingState build() => const BriefingState();

  Future<void> generate() async {
    state = BriefingState(loading: true, briefing: state.briefing);
    try {
      final briefing = await ref.read(briefingRepositoryProvider).generate();
      state = BriefingState(briefing: briefing);
    } catch (e) {
      state = BriefingState(error: friendlyError(e), briefing: state.briefing);
    }
  }
}

final briefingProvider = NotifierProvider<BriefingNotifier, BriefingState>(
  BriefingNotifier.new,
);
